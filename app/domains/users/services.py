from app.domains.auth import AuthSession, CurrentUser
from app.domains.auth.models import EmailVerificationToken

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from beanie import PydanticObjectId
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError
from pymongo.asynchronous.client_session import AsyncClientSession
from fastapi import UploadFile

from app.core.config import Settings
from app.core.repositories import BaseRepository, TenantRepository
from app.core.security import (
    create_one_time_token,
    hash_one_time_token,
    hash_password,
    verify_password,
)
from app.shared.enums import AuthProvider, Role, UserStatus
from app.shared.errors.exceptions import AppException
from app.shared.services.permissions import PLATFORM_ROLES
from app.integrations.cloudinary import CloudinaryService
from app.domains.bussines.models import Business
from app.domains.users.models import User
from app.domains.users.schemas import (
    AdminResetPassword,
    PasswordSelfUpdate,
    UserCreate,
    UserSelfUpdate,
    UserUpdate,
    UserCreationResponse,
)


class TenantUserService:

    # ================================================================
    # Servicios administrativos del tenant
    # ================================================================

    # Mapa de jerarquía: menor número = mayor poder.
    ROLE_HIERARCHY = {
        Role.SUPERADMIN: 0,
        Role.ADMIN: 1,
        Role.PROPIETARIO: 2,
        Role.GERENTE: 3,
        Role.FINANZAS: 4,
        Role.VENDEDOR: 5,
        Role.ALMACEN: 6,
        Role.USER: 7,
    }

    @staticmethod
    def _check_tenant_hierarchy(actor: CurrentUser, target: User) -> None:
        """Valida jerarquía estricta."""

        actor_level = TenantUserService.ROLE_HIERARCHY.get(actor.role, 99)
        target_level = TenantUserService.ROLE_HIERARCHY.get(target.role, 99)

        if actor_level >= target_level:
            raise AppException("No tienes permisos para gestionar a este usuario",403)

    @staticmethod
    async def _get_active_tenant_user(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
    ) -> User:
        """Obtiene un usuario no eliminado desde el repositorio recibido."""
        user = await repository.get(user_id)
        if not user:
            raise AppException("Usuario no existente", 404)
        if user.is_deleted:
            raise AppException("Usuario eliminado", 404)
        return user

    @staticmethod
    async def create_tenant_user(
        repository: TenantRepository[User],
        global_repository: BaseRepository[User],
        user_data: UserCreate,
        actor: CurrentUser,
        mongodb_client: AsyncMongoClient,
        settings: Settings,
    ) -> UserCreationResponse:
        """Crea un usuario, su token y envía el correo de verificación."""
        from app.domains.auth.services import AuthService

        now = datetime.now(timezone.utc)

        async def create_user_and_token(session: AsyncClientSession) -> tuple[User, str]:

            actor_level = TenantUserService.ROLE_HIERARCHY.get(actor.role, 99)
            target_level = TenantUserService.ROLE_HIERARCHY.get(user_data.role, 99)

            if actor_level >= target_level:
                raise AppException("No tienes permisos para crear un usuario con este rol",403)

            username = None
            if user_data.username:
                cleaned_username = user_data.username.strip().lower()
                if cleaned_username:
                    username = cleaned_username

            existing_user = await global_repository.find_one({"email": user_data.email})
            if existing_user:
                raise AppException("El email ya está registrado.", 409)

            if username:
                existing_username = await global_repository.find_one({"username": username})
                if existing_username:
                    raise AppException("El username ya está en uso.", 409)

            new_user = User(
                email=user_data.email,
                username=username,
                name=user_data.name,
                lastname=user_data.lastname,
                password_hash=hash_password(user_data.password),
                role=user_data.role,
                status=UserStatus.PENDING_VERIFICATION,
                email_verified=False,
                auth_provider=AuthProvider.LOCAL,
                avatar_url=None,
                phone_number=user_data.phone_number,
                birth_date=user_data.birth_date,
                created_by=actor.id,
                updated_by=actor.id,
            )
            created_user = await repository.create(new_user, session=session)

            verification_token_value = create_one_time_token()
            verification_token = EmailVerificationToken(
                user_id=created_user.id,
                token_hash=hash_one_time_token(verification_token_value),
                expires_at=now + timedelta(hours=AuthService.VERIFICATION_TOKEN_EXPIRE_HOURS),
            )
            await verification_token.insert(session=session)
            return created_user, verification_token_value

        try:
            async with mongodb_client.start_session() as session:
                created_user, verification_token_value = (await session.with_transaction(create_user_and_token))
        except DuplicateKeyError as error:
            raise AppException("El email o username ya está registrado.",409) from error
        
        verification_email_sent = True
        try:
            await AuthService.deliver_verification_email(
                email=str(created_user.email),
                token_value=verification_token_value,
                settings=settings,
            )
        except Exception:
            verification_email_sent = False
        return UserCreationResponse(
            user=created_user,
            verification_email_sent=verification_email_sent,
            message=("Usuario creado y correo de verificación enviado."if verification_email_sent
            else "Usuario creado, pero no se pudo enviar el correo."),
        )

    @staticmethod
    async def list_tenant_users(
        repository: TenantRepository[User],
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        role: Role | None = None,
        user_status: UserStatus | None = None,
    ) -> dict[str, Any]:
        """Lista usuarios del tenant autorizado con filtros y paginación."""
        filters: dict[str, Any] = {"is_deleted": False}

        if q:
            safe_q = re.escape(q)
            filters["$or"] = [
                {"email": {"$regex": safe_q, "$options": "i"}},
                {"username": {"$regex": safe_q, "$options": "i"}},
                {"name": {"$regex": safe_q, "$options": "i"}},
                {"lastname": {"$regex": safe_q, "$options": "i"}},
                {"phone_number": {"$regex": safe_q, "$options": "i"}},
            ]

        if role is not None:
            filters["role"] = role

        if user_status is not None:
            filters["status"] = user_status

        total_count = await repository.count(filters)
        skip = (page - 1) * per_page
        users = await repository.list(
            filters,
            skip=skip,
            limit=per_page,
            sort=(+User.created_at,),
        )

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total_count / per_page) if per_page > 0 else 0,
            "data": users,
        }

    @staticmethod
    async def get_tenant_user(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
    ) -> User:
        """Obtiene un usuario activo dentro del tenant del repositorio."""
        user = await TenantUserService._get_active_tenant_user(repository, user_id)
        return user

    @staticmethod
    async def update_tenant_user(
        repository: TenantRepository[User],
        global_repository: BaseRepository[User],
        user_id: PydanticObjectId,
        update_data: UserUpdate,
        actor: CurrentUser,
    ) -> User:
        """Actualiza datos administrativos del usuario autorizado."""
        user = await TenantUserService._get_active_tenant_user(repository, user_id)
        TenantUserService._check_tenant_hierarchy(actor, user)

        if update_data.username is not None and update_data.username != user.username:
            existing = await global_repository.find_one(
                {
                    "username": update_data.username,
                    "_id": {"$ne": user.id},
                }
            )
            if existing:
                raise AppException("El username ya está en uso", 409)

        update_dict = update_data.model_dump(exclude_unset=True)
        proposed_role = update_dict.get("role")
        if proposed_role is not None:
            actor_level = TenantUserService.ROLE_HIERARCHY.get(actor.role, 99)
            proposed_level = TenantUserService.ROLE_HIERARCHY.get(proposed_role, 99)
            if actor_level >= proposed_level:
                raise AppException("No tienes permisos para asignar este rol al usuario",403)

        for key, value in update_dict.items():
            setattr(user, key, value)

        user.updated_by = actor.id
        saved_user = await repository.save(user)

        if ("status" in update_dict and user.status != UserStatus.ACTIVE):
            await AuthSession.revoke_for_user(user.id,"user_status_changed_by_tenant")
        return saved_user

    @staticmethod
    async def reset_tenant_user_password(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
        data: AdminResetPassword,
        actor: CurrentUser,
    ) -> None:
        """Restablece administrativamente la contraseña de un usuario."""
        user = await TenantUserService._get_active_tenant_user(repository, user_id)
        TenantUserService._check_tenant_hierarchy(actor, user)

        user.password_hash = hash_password(data.new_password)
        user.updated_by = actor.id
        await repository.save(user)
        await AuthSession.revoke_for_user(user.id,"password_reset_by_tenant")

    @staticmethod
    async def delete_tenant_user(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
        actor: CurrentUser,
    ) -> None:
        """
        Elimina un usuario: soft delete.
        """

        user = await TenantUserService._get_active_tenant_user(repository, user_id)
        TenantUserService._check_tenant_hierarchy(actor, user)

        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by = actor.id
        user.updated_by = actor.id

        await repository.save(user)
        await AuthSession.revoke_for_user(user.id,"user_deleted_by_tenant")





class UserSelfService:

    # ================================================================
    # Servicios de autogestión del usuario (/me)
    # ================================================================

    @staticmethod
    async def update_my_avatar(
        repository: BaseRepository[User],
        file: UploadFile,
        actor: User,
    ) -> User:
        """Actualiza el avatar del usuario autenticado."""
        new_avatar_url = await CloudinaryService.upload_image(file, folder="avatars")
        old_avatar_url = actor.avatar_url

        actor.avatar_url = new_avatar_url
        actor.updated_by = actor.id
        await repository.save(actor)

        if old_avatar_url is not None:
            await CloudinaryService.delete_image(old_avatar_url)
        return actor

    @staticmethod
    async def update_my_profile(
        repository: BaseRepository[User],
        update_data: UserSelfUpdate,
        actor: User,
    ) -> User:
        """Actualiza el perfil del usuario autenticado."""
        if update_data.username is not None and update_data.username != actor.username:
            existing = await repository.find_one(
                {
                    "username": update_data.username,
                    "_id": {"$ne": actor.id},
                }
            )
            if existing:
                raise AppException("El username ya está en uso", 409)

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(actor, key, value)

        actor.updated_by = actor.id
        return await repository.save(actor)

    @staticmethod
    async def change_my_password(
        repository: BaseRepository[User],
        user: User,
        data: PasswordSelfUpdate,
    ) -> None:
        """Cambia la contraseña del usuario autenticado."""
        if not user.password_hash or not verify_password(
            data.current_password,
            user.password_hash,
        ):
            raise AppException("Contraseña actual incorrecta", 401)

        user.password_hash = hash_password(data.new_password)
        user.updated_by = user.id
        await repository.save(user)
        await AuthSession.revoke_for_user(user.id,"password_changed")


class PlatformUserService:
    """Servicios administrativos globales para usuarios de plataforma."""

    # ================================================================
    # Servicios administrativos de plataforma
    # ================================================================

    ROLE_HIERARCHY = TenantUserService.ROLE_HIERARCHY


    @staticmethod
    def _check_platform_hierarchy(actor: CurrentUser, target: User) -> None:
        actor_level = PlatformUserService.ROLE_HIERARCHY.get(actor.role, 99)
        target_level = PlatformUserService.ROLE_HIERARCHY.get(target.role, 99)
        if actor_level >= target_level:
            raise AppException("No tienes permisos para gestionar a este usuario",403)

    @staticmethod
    async def _get_active_platform_user(repository: BaseRepository[User],user_id: PydanticObjectId) -> User:
        """Obtiene un usuario activo desde el repositorio global."""
        user = await repository.get(user_id)
        if not user:
            raise AppException("Usuario no existente", 404)
        if user.is_deleted:
            raise AppException("Usuario eliminado", 404)
        if user.status != UserStatus.ACTIVE:
            raise AppException("Usuario inactivo", 403)
        return user

    @staticmethod
    async def create_platform_user(
        repository: BaseRepository[User],
        global_repository: BaseRepository[User],
        user_data: UserCreate,
        actor: CurrentUser,
        mongodb_client: AsyncMongoClient,
        settings: Settings,
        business_id: PydanticObjectId | None = None,
        business_repository: BaseRepository[Business] | None = None,
    ) -> User:
        """Crea un usuario global o asociado a un negocio seleccionado."""
        


        if business_id is not None:
            if business_repository is None:
                raise AppException("Repositorio de negocio requerido.", 500)

            business = await business_repository.get(business_id)
            if not business or business.is_deleted:
                raise AppException("Empresa no existente.", 404)

        now = datetime.now(timezone.utc)

        async def create_user_and_token(
            session: AsyncClientSession,
        ) -> tuple[User, str]:
            actor_level = PlatformUserService.ROLE_HIERARCHY.get(actor.role, 99)
            target_level = PlatformUserService.ROLE_HIERARCHY.get(user_data.role, 99)

            if actor_level >= target_level:
                raise AppException(
                    "No tienes permisos para crear un usuario con este rol",
                    403,
                )

            username = None
            if user_data.username:
                cleaned_username = user_data.username.strip().lower()
                if cleaned_username:
                    username = cleaned_username

            existing_user = await global_repository.find_one(
                {"email": user_data.email}
            )
            if existing_user:
                raise AppException("El email ya está registrado.", 409)

            if username:
                existing_username = await global_repository.find_one(
                    {"username": username}
                )
                if existing_username:
                    raise AppException("El username ya está en uso.", 409)

            new_user = User(
                email=user_data.email,
                username=username,
                name=user_data.name,
                lastname=user_data.lastname,
                password_hash=hash_password(user_data.password),
                role=user_data.role,
                status=UserStatus.PENDING_VERIFICATION,
                email_verified=False,
                auth_provider=AuthProvider.LOCAL,
                avatar_url=None,
                phone_number=user_data.phone_number,
                birth_date=user_data.birth_date,
                business_id=business_id,
                created_by=actor.id,
                updated_by=actor.id,
            )

            created_user = await repository.create(new_user, session=session)

            verification_token_value = create_one_time_token()
            verification_token = EmailVerificationToken(
                user_id=created_user.id,
                token_hash=hash_one_time_token(verification_token_value),
                expires_at=now + timedelta(
                    hours=AuthService.VERIFICATION_TOKEN_EXPIRE_HOURS
                ),
            )
            await verification_token.insert(session=session)
            return created_user, verification_token_value

        try:
            async with mongodb_client.start_session() as session:
                created_user, verification_token_value = (
                    await session.with_transaction(create_user_and_token)
                )
        except DuplicateKeyError as error:
            raise AppException(
                "El email o username ya está registrado.",
                409,
            ) from error

        await AuthService.deliver_verification_email(
            email=str(created_user.email),
            token_value=verification_token_value,
            settings=settings,
        )
        return created_user

    @staticmethod
    async def list_platform_users(
        repository: BaseRepository[User],
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        role: Role | None = None,
        user_status: UserStatus | None = None,
        business_id: PydanticObjectId | None = None,
    ) -> dict[str, Any]:
        """Lista usuarios globalmente, con filtro opcional por negocio."""
        filters: dict[str, Any] = {"is_deleted": False}

        if business_id is not None:
            filters["business_id"] = business_id

        if q:
            safe_q = re.escape(q)
            filters["$or"] = [
                {"email": {"$regex": safe_q, "$options": "i"}},
                {"username": {"$regex": safe_q, "$options": "i"}},
                {"name": {"$regex": safe_q, "$options": "i"}},
                {"lastname": {"$regex": safe_q, "$options": "i"}},
                {"phone_number": {"$regex": safe_q, "$options": "i"}},
            ]

        if role is not None:
            filters["role"] = role

        if user_status is not None:
            filters["status"] = user_status

        total_count = await repository.count(filters)
        skip = (page - 1) * per_page
        users = await repository.list(
            filters,
            skip=skip,
            limit=per_page,
            sort=(+User.created_at,),
        )

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total_count / per_page) if per_page > 0 else 0,
            "data": users,
        }

    @staticmethod
    async def get_platform_user(
        repository: BaseRepository[User],
        user_id: PydanticObjectId,
    ) -> User:
        """Obtiene cualquier usuario mediante el repositorio global."""
        return await PlatformUserService._get_active_platform_user(
            repository,
            user_id,
        )

    @staticmethod
    async def update_platform_user(
        repository: BaseRepository[User],
        global_repository: BaseRepository[User],
        user_id: PydanticObjectId,
        update_data: UserUpdate,
        actor: CurrentUser,
    ) -> User:
        """Actualiza administrativamente cualquier usuario autorizado."""
        user = await PlatformUserService._get_active_platform_user(
            repository,
            user_id,
        )
        PlatformUserService._check_platform_hierarchy(actor, user)

        if update_data.username is not None and update_data.username != user.username:
            existing = await global_repository.find_one(
                {
                    "username": update_data.username,
                    "_id": {"$ne": user.id},
                }
            )
            if existing:
                raise AppException("El username ya está en uso", 409)

        update_dict = update_data.model_dump(exclude_unset=True)
        proposed_role = update_dict.get("role")
        if proposed_role is not None:
            actor_level = PlatformUserService.ROLE_HIERARCHY.get(actor.role, 99)
            proposed_level = PlatformUserService.ROLE_HIERARCHY.get(
                proposed_role,
                99,
            )
            if actor_level >= proposed_level:
                raise AppException(
                    "No tienes permisos para asignar este rol al usuario",
                    403,
                )

        for key, value in update_dict.items():
            setattr(user, key, value)

        user.updated_by = actor.id
        saved_user = await repository.save(user)

        if "status" in update_dict and user.status != UserStatus.ACTIVE:
            await AuthSession.revoke_for_user(user.id, "user_status_changed")
        return saved_user

    @staticmethod
    async def reset_platform_user_password(
        repository: BaseRepository[User],
        user_id: PydanticObjectId,
        data: AdminResetPassword,
        actor: CurrentUser,
    ) -> None:
        """Restablece la contraseña de cualquier usuario autorizado."""
        user = await PlatformUserService._get_active_platform_user(
            repository,
            user_id,
        )
        PlatformUserService._check_platform_hierarchy(actor, user)

        user.password_hash = hash_password(data.new_password)
        user.updated_by = actor.id
        await repository.save(user)
        await AuthSession.revoke_for_user(user.id, "admin_password_reset")

    @staticmethod
    async def delete_platform_user(
        repository: BaseRepository[User],
        user_id: PydanticObjectId,
        actor: CurrentUser,
    ) -> None:
        """Realiza el borrado lógico de cualquier usuario autorizado."""
        user = await PlatformUserService._get_active_platform_user(
            repository,
            user_id,
        )
        PlatformUserService._check_platform_hierarchy(actor, user)

        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by = actor.id
        user.updated_by = actor.id

        await repository.save(user)
        await AuthSession.revoke_for_user(user.id, "user_deleted")
