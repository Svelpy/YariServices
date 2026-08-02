import math
import re
from datetime import datetime, timezone
from typing import Any, Dict

from beanie import PydanticObjectId
from beanie.operators import Or, RegEx

from app.domains.bussines.models import Business
from app.domains.bussines.schemas import BusinessCreate, BusinessUpdate
from app.domains.users.models import User
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug


class BusinessService:

    @staticmethod
    async def create_business(data: BusinessCreate, actor: User) -> Business:
        """
        Crea una nueva empresa (Acción Administrativa).
        Asigna la empresa al usuario especificado en data.owner_id y actualiza su rol a PROPIETARIO.
        """
        # Verificar que el usuario asignado como propietario exista
        owner_user = await User.get(data.owner_id)
        if not owner_user or owner_user.is_deleted:
            raise AppException("El usuario asignado como propietario no existe o fue eliminado.", 404)

        # Generar slug a partir del nombre
        slug = generate_slug(data.name)
        if not slug:
            raise AppException("El nombre proporcionado no genera un slug válido.", 400)

        # Verificar unicidad del slug en empresas activas
        existing_slug = await Business.find_one(
            Business.slug == slug,
            Business.is_deleted == False,
        )
        if existing_slug:
            raise AppException(f"El slug '{slug}' ya está registrado para otra empresa.", 409)

        # Verificar si el usuario ya es propietario de otra empresa activa
        existing_owner = await Business.find_one(
            Business.owner_id == owner_user.id,
            Business.is_deleted == False,
        )
        if existing_owner:
            raise AppException("El usuario seleccionado ya es propietario de una empresa registrada.", 409)

        # Instanciar nueva empresa
        business = Business(
            name=data.name,
            slug=slug,
            owner_id=owner_user.id,
            is_active=True,
            created_by=actor.id,
            updated_by=actor.id,
        )
        await business.save()

        # Vincular empresa y actualizar rol en la cuenta del dueño asignado
        owner_user.business_id = business.id
        if owner_user.role != Role.PROPIETARIO:
            owner_user.role = Role.PROPIETARIO
        owner_user.updated_by = actor.id
        await owner_user.save()

        return business

    @staticmethod
    async def get_business(business_id: PydanticObjectId) -> Business:
        """
        Obtiene una empresa activa por su ID.
        """
        business = await Business.get(business_id)
        if not business or business.is_deleted:
            raise AppException("Empresa no existente.", 404)
        return business

    @staticmethod
    async def get_business_by_slug(slug: str) -> Business:
        """
        Obtiene una empresa activa por su slug público.
        """
        business = await Business.find_one(
            Business.slug == slug,
            Business.is_deleted == False,
        )
        if not business:
            raise AppException("Empresa no encontrada.", 404)
        return business

    @staticmethod
    async def list_businesses(
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> Dict[str, Any]:
        """
        Lista empresas registradas con soporte para búsqueda por texto, filtro de estado y paginación.
        """
        query = Business.find(Business.is_deleted == False)

        if is_active is not None:
            query = query.find(Business.is_active == is_active)

        if q:
            safe_q = re.escape(q)
            query = query.find(Or(
                RegEx(Business.name, safe_q, "i"),
                RegEx(Business.slug, safe_q, "i"),
            ))

        total_count = await query.count()
        skip = (page - 1) * per_page
        businesses = await query.sort(+Business.created_at).skip(skip).limit(per_page).to_list()
        total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "data": businesses,
        }

    @staticmethod
    async def update_business(
        business_id: PydanticObjectId,
        update_data: BusinessUpdate,
        actor: User,
    ) -> Business:
        """
        Actualiza los datos de una empresa (nombre, estado).
        Recalcula el slug si el nombre cambia.
        """
        business = await BusinessService.get_business(business_id)

        # Validar permisos: solo el dueño o administradores de plataforma pueden editar
        if actor.role not in [Role.SUPERADMIN, Role.ADMIN] and actor.id != business.owner_id:
            raise AppException("No tienes permisos para modificar esta empresa.", 403)

        update_dict = update_data.model_dump(exclude_unset=True)

        if ("name" in update_dict) and (update_dict["name"] != business.name):
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException("El nombre proporcionado no genera un slug válido.", 400)

            existing_slug = await Business.find_one(
                Business.slug == new_slug,
                Business.id != business.id,
                Business.is_deleted == False,
            )
            if existing_slug:
                raise AppException(f"El slug '{new_slug}' ya está registrado para otra empresa.", 409)
            update_dict["slug"] = new_slug

        for key, value in update_dict.items():
            setattr(business, key, value)

        business.updated_by = actor.id
        await business.save()
        return business

    @staticmethod
    async def delete_business(
        business_id: PydanticObjectId,
        actor: User,
        hard_delete: bool = False,
    ) -> None:
        """
        Elimina una empresa (soft delete por defecto, hard delete para SUPERADMIN).
        """
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException("Solo un SUPERADMIN puede realizar un borrado permanente.", 403)

        business = await BusinessService.get_business(business_id)

        if actor.role not in [Role.SUPERADMIN, Role.ADMIN] and actor.id != business.owner_id:
            raise AppException("No tienes permisos para eliminar esta empresa.", 403)

        if hard_delete:
            await business.delete()
        else:
            now = datetime.now(timezone.utc)
            business.is_deleted = True
            business.deleted_at = now
            business.deleted_by = actor.id
            business.updated_by = actor.id
            await business.save()
