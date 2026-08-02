import math
import re
from datetime import datetime, timezone
from typing import Any, Dict

from beanie import PydanticObjectId
from beanie.operators import Or, RegEx
from fastapi import UploadFile

from app.core.security import hash_password, verify_password
from app.domains.users import (
    AdminResetPassword,
    PasswordSelfUpdate,
    User,
    UserCreate,
    UserSelfUpdate,
    UserUpdate,
)
from app.integrations.cloudinary import CloudinaryService
from app.shared.enums import AuthProvider, Role, UserStatus
from app.shared.errors.exceptions import AppException
from app.shared.services.permissions import PLATFORM_ROLES


class UserService:

    # ─────────────────────────────────────────────
    # HELPERS INTERNOS
    # ─────────────────────────────────────────────

    # Mapa de jerarquía: menor número = mayor poder
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
    def _check_hierarchy(actor: User, target: User):
        """
        Valida jerarquía estricta y aislamiento de tenant (empresa).
        """
        if actor.role not in PLATFORM_ROLES and target.business_id != actor.business_id:
            raise AppException("No tienes permisos para gestionar a un usuario de otra empresa", 403)

        actor_level = UserService.ROLE_HIERARCHY.get(actor.role, 99)
        target_level = UserService.ROLE_HIERARCHY.get(target.role, 99)

        if actor_level >= target_level:
            raise AppException("No tienes permisos para gestionar a este usuario", 403)

    @staticmethod
    async def _get_active_user(user_id: PydanticObjectId) -> User:
        """
        Obtiene un usuario activo por ID (PydanticObjectId).
        FastAPI/Beanie validan el formato del ID automáticamente.
        """
        user = await User.get(user_id)
        if not user:
            raise AppException("Usuario no existente", 404)
        if user.is_deleted:
            raise AppException("Usuario eliminado", 404)
        return user

    # ─────────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────────
    @staticmethod
    async def register_user(user_data: UserCreate, actor: User) -> User:
        """
        Registrar un nuevo usuario (administrativo).
        """
        actor_level = UserService.ROLE_HIERARCHY.get(actor.role, 99)
        target_level = UserService.ROLE_HIERARCHY.get(user_data.role, 99)

        if actor_level >= target_level:
            raise AppException("No tienes permisos para crear un usuario con este rol", 403)
        #-----------------------------------------------------------------------------------
        username = None
        if user_data.username:
            cleaned_username = user_data.username.strip().lower()
            if cleaned_username != "":
                username = cleaned_username

        # Verificar si el email ya existe
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise AppException("El email ya está registrado.", 409)

        # Verificar si el username ya existe
        if username:
            existing_username = await User.find_one(User.username == username)
            if existing_username:
                raise AppException("El username ya está en uso.", 409)

        # Crear nuevo usuario con asignación opcional de empresa (business_id)
        new_user = User(
            email=user_data.email,
            username=username,
            name=user_data.name,
            lastname=user_data.lastname,
            password_hash=hash_password(user_data.password),
            role=user_data.role,
            business_id=user_data.business_id,
            status=UserStatus.ACTIVE,
            email_verified=False,
            auth_provider=AuthProvider.LOCAL,
            avatar_url=None,
            phone_number=user_data.phone_number,
            birth_date=user_data.birth_date,
            created_by=actor.id,
            updated_by=actor.id,
        )

        await new_user.save()
        return new_user

    @staticmethod
    async def list_users(
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        role: Role | None = None,
        user_status: UserStatus | None = None,
        business_id: PydanticObjectId | None = None,
    ) -> Dict[str, Any]:
        """Lista usuarios con paginación y filtros opcionales (incluye filtro por business_id)."""
        query = User.find(User.is_deleted == False)

        if business_id is not None:
            query = query.find(User.business_id == business_id)

        # Búsqueda por texto en email, username, name y lastname
        if q:
            safe_q = re.escape(q)
            query = query.find(Or(
                RegEx(User.email, safe_q, "i"),
                RegEx(User.username, safe_q, "i"),
                RegEx(User.name, safe_q, "i"),
                RegEx(User.lastname, safe_q, "i"),
                RegEx(User.phone_number, safe_q, "i"),
            ))

        if role is not None:
            query = query.find(User.role == role)

        if user_status is not None:
            query = query.find(User.status == user_status)

        total_count = await query.count()
        skip = (page - 1) * per_page
        users = await query.sort(+User.created_at).skip(skip).limit(per_page).to_list()
        total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "data": users,
        }

    @staticmethod
    async def get_user(user_id: PydanticObjectId, actor: User | None = None) -> User:
        """Obtiene un usuario activo por ID."""
        user = await UserService._get_active_user(user_id)
        if actor and actor.role not in PLATFORM_ROLES and user.business_id != actor.business_id:
            raise AppException("No tienes permisos para ver a este usuario", 403)
        return user

    @staticmethod
    async def update_user(user_id: PydanticObjectId, update_data: UserUpdate, actor: User) -> User:
        """Actualiza datos del usuario (incluyendo rol, estado o business_id) con validación de jerarquía y unicidad."""
        user = await UserService._get_active_user(user_id)

        # Validación estricta: Mismo rango y autogestión no están permitidos en rutas administrativas
        UserService._check_hierarchy(actor, user)

        # Validar unicidad de username
        if update_data.username is not None and update_data.username != user.username:
            existing = await User.find_one(User.username == update_data.username)
            if existing:
                raise AppException("El username ya está en uso", 409)

        # Validar unicidad de email
        if update_data.email is not None and update_data.email != user.email:
            existing_email = await User.find_one(User.email == update_data.email)
            if existing_email:
                raise AppException("El email ya está en uso", 409)

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(user, key, value)

        user.updated_by = actor.id
        await user.save()
        return user

    @staticmethod
    async def update_avatar(user_id: PydanticObjectId, file: UploadFile, actor: User) -> User:
        """Actualiza el avatar del usuario subiendo la imagen a Cloudinary"""
        user = await UserService._get_active_user(user_id)

        # Validación estricta: Mismo rango y autogestión no están permitidos en rutas administrativas
        UserService._check_hierarchy(actor, user)

        new_avatar_url = await CloudinaryService.upload_image(file, folder="avatars")
        old_avatar_url = user.avatar_url

        user.avatar_url = new_avatar_url
        user.updated_by = actor.id
        await user.save()
        if old_avatar_url is not None:
            await CloudinaryService.delete_image(old_avatar_url)
        return user

    @staticmethod
    async def reset_password(user_id: PydanticObjectId, data: AdminResetPassword, actor: User) -> None:
        """Restablece la contraseña de un usuario"""
        user = await UserService._get_active_user(user_id)

        # Restablecer contraseña requiere jerarquía estricta
        UserService._check_hierarchy(actor, user)

        user.password_hash = hash_password(data.new_password)
        user.updated_by = actor.id
        await user.save()

    @staticmethod
    async def delete_user(user_id: PydanticObjectId, actor: User, hard_delete: bool = False) -> None:
        """
        Elimina un usuario:
        - ADMIN → Soft delete (borrado lógico).
        - SUPERADMIN → Hard delete (borrado físico permanente).
        """
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException("Solo un SUPERADMIN puede realizar un borrado permanente.", 403)

        user = await UserService._get_active_user(user_id)

        # La jerarquía ya maneja si intento eliminar mi propia cuenta (mismo nivel -> falla)
        UserService._check_hierarchy(actor, user)
        if hard_delete:
            # Hard delete físico
            await user.delete()
        else:
            # Soft delete
            user.is_deleted = True
            user.deleted_at = datetime.now(timezone.utc)
            user.deleted_by = actor.id
            user.updated_by = actor.id
            await user.save()

    @staticmethod
    async def update_profile(update_data: UserSelfUpdate, actor: User) -> User:
        """
        Actualiza el perfil del propio usuario autenticado (autogestión).
        UserSelfUpdate no expone el campo email, por eso no se valida aquí.
        """
        # Validar unicidad de username (si está cambiando)
        if update_data.username is not None and update_data.username != actor.username:
            existing = await User.find_one(User.username == update_data.username)
            if existing:
                raise AppException("El username ya está en uso", 409)

        update_dict = update_data.model_dump(exclude_unset=True)
        # Aplicar los cambios al objeto del actor
        for key, value in update_dict.items():
            setattr(actor, key, value)
        actor.updated_by = actor.id
        await actor.save()
        return actor

    @staticmethod
    async def change_password(user: User, data: PasswordSelfUpdate) -> None:
        """
        Cambiar contraseña del propio usuario autenticado.
        """
        # Verificar contraseña actual
        if not user.password_hash or not verify_password(data.current_password, user.password_hash):
            raise AppException("Contraseña actual incorrecta", 401)

        # Actualizar contraseña
        user.password_hash = hash_password(data.new_password)
        await user.save()

    @staticmethod
    async def update_avatar_self(file: UploadFile, actor: User) -> User:
        """
        Actualiza el avatar del propio usuario autenticado (autogestión).
        """
        new_avatar_url = await CloudinaryService.upload_image(file, folder="avatars")
        old_avatar_url = actor.avatar_url

        actor.avatar_url = new_avatar_url
        actor.updated_by = actor.id
        await actor.save()

        if old_avatar_url is not None:
            await CloudinaryService.delete_image(old_avatar_url)
        return actor
