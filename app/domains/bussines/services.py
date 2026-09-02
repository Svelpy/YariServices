import math
import re
from datetime import datetime, timezone
from typing import Any

from beanie import PydanticObjectId
from fastapi import UploadFile

from app.core.repositories import BaseRepository
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug
from app.integrations.cloudinary import CloudinaryService
from app.domains.auth import CurrentUser
from app.domains.bussines.models import Business
from app.domains.bussines.schemas import BusinessMeUpdate, BusinessUpdate


class BusinessService:

    @staticmethod
    async def get_business(repository: BaseRepository[Business],business_id: PydanticObjectId) -> Business:
        business = await repository.get(business_id)
        if not business or business.is_deleted:
            raise AppException("Empresa no existente.", 404)
        return business

    @staticmethod
    async def list_businesses(
        repository: BaseRepository[Business],
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {
            "is_deleted": False,
        }

        if is_active is not None:
            filters["is_active"] = is_active

        if q:
            safe_q = re.escape(q)
            filters["$or"] = [
                {"name": {"$regex": safe_q, "$options": "i"}},
                {"slug": {"$regex": safe_q, "$options": "i"}},
            ]

        total_count = await repository.count(filters)
        skip = (page - 1) * per_page
        businesses = await repository.list(
            filters,
            skip=skip,
            limit=per_page,
            sort=(+Business.created_at,),
        )

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total_count / per_page) if per_page > 0 else 0,
            "data": businesses,
        }

    @staticmethod
    async def update_business(
        repository: BaseRepository[Business],
        business_id: PydanticObjectId,
        update_data: BusinessUpdate | BusinessMeUpdate,
        actor: CurrentUser,
    ) -> Business:
        """Actualiza una empresa respetando los permisos del actor."""
        business = await BusinessService.get_business(repository, business_id)

        update_dict = update_data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"] != business.name:
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException("El nombre proporcionado no genera un slug válido.",400)

            existing_slug = await repository.find_one(
                {
                    "slug": new_slug,
                    "_id": {"$ne": business.id},
                    "is_deleted": False,
                }
            )
            if existing_slug:
                raise AppException(f"El slug '{new_slug}' ya está registrado para otra empresa.",409)
            update_dict["slug"] = new_slug

        for key, value in update_dict.items():
            setattr(business, key, value)

        business.updated_by = actor.id
        return await repository.save(business)

    @staticmethod
    async def update_my_business(
        repository: BaseRepository[Business],
        update_data: BusinessMeUpdate,
        actor: CurrentUser,
    ) -> Business:
        """Actualiza el negocio propio del usuario autenticado."""
        if actor.business_id is None:
            raise AppException("El usuario no tiene una empresa asignada.", 404)

        return await BusinessService.update_business(
            repository=repository,
            business_id=actor.business_id,
            update_data=update_data,
            actor=actor,
        )

    @staticmethod
    async def delete_business(
        repository: BaseRepository[Business],
        business_id: PydanticObjectId,
        actor: CurrentUser,
        hard_delete: bool = False,
    ) -> None:
        """Elimina una empresa de forma lógica o permanente."""
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException("Solo un SUPERADMIN puede realizar un borrado permanente.",403)

        business = await BusinessService.get_business(repository, business_id)

        if actor.role not in {Role.SUPERADMIN, Role.ADMIN}:
            raise AppException("No tienes permisos para eliminar esta empresa.", 403)

        if hard_delete:
            await repository.delete(business)
            return

        now = datetime.now(timezone.utc)
        business.is_deleted = True
        business.deleted_at = now
        business.deleted_by = actor.id
        business.updated_by = actor.id
        await repository.save(business)

    @staticmethod
    async def update_business_logo(
        repository: BaseRepository[Business],
        business_id: PydanticObjectId,
        file: UploadFile,
        actor: CurrentUser,
    ) -> Business:
        business = await BusinessService.get_business(repository, business_id)

        old_logo_url = business.logo_url
        new_logo_url = await CloudinaryService.upload_image(
            file,
            folder="businesses",
        )

        business.logo_url = new_logo_url
        business.updated_by = actor.id

        business = await repository.save(business)

        if old_logo_url:
            await CloudinaryService.safe_delete_image(old_logo_url)

        return business

    @staticmethod
    async def update_my_business_logo(
        repository: BaseRepository[Business],
        file: UploadFile,
        actor: CurrentUser,
    ) -> Business:
        if actor.business_id is None:
            raise AppException("El usuario no tiene una empresa asignada.", 404)

        return await BusinessService.update_business_logo(
            repository=repository,
            business_id=actor.business_id,
            file=file,
            actor=actor,
        )
