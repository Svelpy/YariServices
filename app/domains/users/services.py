import math
import re
from datetime import datetime, timezone
from typing import Any

from beanie import PydanticObjectId
from fastapi import UploadFile

from app.core.repositories import BaseRepository, TenantRepository
from app.core.security import hash_password, verify_password
from app.shared.enums import AuthProvider, Role, UserStatus
from app.shared.errors.exceptions import AppException
from app.shared.services.permissions import PLATFORM_ROLES
from app.integrations.cloudinary import CloudinaryService
from app.domains.users.models import User
from app.domains.users.schemas import (
    AdminResetPassword,
    PasswordSelfUpdate,
    UserCreate,
    UserSelfUpdate,
    UserUpdate,
)


class UserService:

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
    def _check_hierarchy(actor: User, target: User) -> None:
        """Valida jerarquía estricta y aislamiento de tenant."""
        if actor.role not in PLATFORM_ROLES and target.business_id != actor.business_id:
            raise AppException(
                "No tienes permisos para gestionar a un usuario de otra empresa",
                403,
            )

        actor_level = UserService.ROLE_HIERARCHY.get(actor.role, 99)
        target_level = UserService.ROLE_HIERARCHY.get(target.role, 99)

        if actor_level >= target_level:
            raise AppException(
                "No tienes permisos para gestionar a este usuario",
                403,
            )

    @staticmethod
    async def _get_active_user(
        repository: BaseRepository[User],
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
    async def register_user(
        repository: TenantRepository[User],
        global_repository: BaseRepository[User],
        user_data: UserCreate,
        actor: User,
    ) -> User:
        """Registra un nuevo usuario dentro del tenant autorizado."""
        actor_level = UserService.ROLE_HIERARCHY.get(actor.role, 99)
        target_level = UserService.ROLE_HIERARCHY.get(user_data.role, 99)

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

        existing_user = await global_repository.find_one({"email": user_data.email})
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
            status=UserStatus.ACTIVE,
            email_verified=False,
            auth_provider=AuthProvider.LOCAL,
            avatar_url=None,
            phone_number=user_data.phone_number,
            birth_date=user_data.birth_date,
            created_by=actor.id,
            updated_by=actor.id,
        )

        # El repositorio fuerza el business_id del contexto autorizado.
        return await repository.create(new_user)

    @staticmethod
    async def list_users(
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
    async def get_user(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
    ) -> User:
        """Obtiene un usuario activo dentro del tenant del repositorio."""
        user = await UserService._get_active_user(repository, user_id)
        return user

    @staticmethod
    async def update_user(
        repository: TenantRepository[User],
        global_repository: BaseRepository[User],
        user_id: PydanticObjectId,
        update_data: UserUpdate,
        actor: User,
    ) -> User:
        """Actualiza datos administrativos del usuario autorizado."""
        user = await UserService._get_active_user(repository, user_id)
        UserService._check_hierarchy(actor, user)

        if update_data.username is not None and update_data.username != user.username:
            existing = await global_repository.find_one(
                {
                    "username": update_data.username,
                    "_id": {"$ne": user.id},
                }
            )
            if existing:
                raise AppException("El username ya está en uso", 409)

        if update_data.email is not None and update_data.email != user.email:
            existing_email = await global_repository.find_one(
                {
                    "email": update_data.email,
                    "_id": {"$ne": user.id},
                }
            )
            if existing_email:
                raise AppException("El email ya está en uso", 409)

        update_dict = update_data.model_dump(exclude_unset=True)
        proposed_role = update_dict.get("role")
        if proposed_role is not None:
            actor_level = UserService.ROLE_HIERARCHY.get(actor.role, 99)
            proposed_level = UserService.ROLE_HIERARCHY.get(proposed_role, 99)
            if actor_level >= proposed_level:
                raise AppException(
                    "No tienes permisos para asignar este rol al usuario",
                    403,
                )

        for key, value in update_dict.items():
            setattr(user, key, value)

        user.updated_by = actor.id
        return await repository.save(user)

    @staticmethod
    async def update_avatar(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
        file: UploadFile,
        actor: User,
    ) -> User:
        """Actualiza el avatar de un usuario administrativamente."""
        user = await UserService._get_active_user(repository, user_id)
        UserService._check_hierarchy(actor, user)

        new_avatar_url = await CloudinaryService.upload_image(file, folder="avatars")
        old_avatar_url = user.avatar_url

        user.avatar_url = new_avatar_url
        user.updated_by = actor.id
        await repository.save(user)

        if old_avatar_url is not None:
            await CloudinaryService.delete_image(old_avatar_url)
        return user

    @staticmethod
    async def reset_password(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
        data: AdminResetPassword,
        actor: User,
    ) -> None:
        """Restablece administrativamente la contraseña de un usuario."""
        user = await UserService._get_active_user(repository, user_id)
        UserService._check_hierarchy(actor, user)

        user.password_hash = hash_password(data.new_password)
        user.updated_by = actor.id
        await repository.save(user)

    @staticmethod
    async def delete_user(
        repository: TenantRepository[User],
        user_id: PydanticObjectId,
        actor: User,
        hard_delete: bool = False,
    ) -> None:
        """
        Elimina un usuario:
        - ADMIN → Soft delete.
        - SUPERADMIN → Hard delete físico.
        """
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException(
                "Solo un SUPERADMIN puede realizar un borrado permanente.",
                403,
            )

        user = await UserService._get_active_user(repository, user_id)
        UserService._check_hierarchy(actor, user)

        if hard_delete:
            await repository.delete(user)
            return

        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        user.deleted_by = actor.id
        user.updated_by = actor.id
        await repository.save(user)

    @staticmethod
    async def update_profile(
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
    async def change_password(
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

    @staticmethod
    async def update_avatar_self(
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
