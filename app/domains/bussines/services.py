import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from beanie import PydanticObjectId

from app.core.repositories import BaseRepository
from app.domains.bussines.models import Business
from app.domains.bussines.schemas import BusinessCreate, BusinessMeUpdate, BusinessUpdate
from app.domains.users.models import User
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug


class BusinessService:

    @staticmethod
    async def create_business(
        repository: BaseRepository[Business],
        user_repository: BaseRepository[User],
        data: BusinessCreate,
        actor: User,
    ) -> Business:
        """Crea una empresa y la vincula con su propietario."""
        owner_user = await user_repository.get(data.owner_id)
        if not owner_user or owner_user.is_deleted:
            raise AppException(
                "El usuario asignado como propietario no existe o fue eliminado.",
                404,
            )

        slug = generate_slug(data.name)
        if not slug:
            raise AppException("El nombre proporcionado no genera un slug válido.", 400)

        existing_slug = await repository.find_one(
            {
                "slug": slug,
                "is_deleted": False,
            }
        )
        if existing_slug:
            raise AppException(
                f"El slug '{slug}' ya está registrado para otra empresa.",
                409,
            )

        existing_owner = await repository.find_one(
            {
                "owner_id": owner_user.id,
                "is_deleted": False,
            }
        )
        if existing_owner:
            raise AppException(
                "El usuario seleccionado ya es propietario de una empresa registrada.",
                409,
            )

        now = datetime.now(timezone.utc)
        business = Business(
            name=data.name,
            slug=slug,
            owner_id=owner_user.id,
            description=data.description,
            logo_url=data.logo_url,
            carousel_url=list(data.carousel_url),
            social_links=dict(data.social_links),
            email=data.email,
            phone=data.phone,
            address=data.address,
            address_google_maps_url=data.address_google_maps_url,
            legal_name=data.legal_name,
            tax_id=data.tax_id,
            country=data.country or "BO",
            currency=data.currency,
            frontend_type=data.frontend_type,
            custom_domain=data.custom_domain,
            plan_started_at=now,
            plan_expires_at=now + timedelta(days=365),
            is_active=True,
            created_by=actor.id,
            updated_by=actor.id,
        )

        business = await repository.create(business)

        owner_user.business_id = business.id
        owner_user.role = Role.PROPIETARIO
        owner_user.updated_by = actor.id
        await user_repository.save(owner_user)

        return business

    @staticmethod
    async def get_business(
        repository: BaseRepository[Business],
        business_id: PydanticObjectId,
    ) -> Business:
        business = await repository.get(business_id)
        if not business or business.is_deleted:
            raise AppException("Empresa no existente.", 404)
        return business

    @staticmethod
    async def get_business_by_slug(
        repository: BaseRepository[Business],
        slug: str,
    ) -> Business:
        business = await repository.find_one(
            {
                "slug": slug,
                "is_deleted": False,
            }
        )
        if not business:
            raise AppException("Empresa no encontrada.", 404)
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
        actor: User,
    ) -> Business:
        """Actualiza una empresa respetando los permisos del actor."""
        business = await BusinessService.get_business(repository, business_id)

        update_dict = update_data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"] != business.name:
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException(
                    "El nombre proporcionado no genera un slug válido.",
                    400,
                )

            existing_slug = await repository.find_one(
                {
                    "slug": new_slug,
                    "_id": {"$ne": business.id},
                    "is_deleted": False,
                }
            )
            if existing_slug:
                raise AppException(
                    f"El slug '{new_slug}' ya está registrado para otra empresa.",
                    409,
                )
            update_dict["slug"] = new_slug

        for key, value in update_dict.items():
            setattr(business, key, value)

        business.updated_by = actor.id
        return await repository.save(business)

    @staticmethod
    async def update_my_business(
        repository: BaseRepository[Business],
        update_data: BusinessMeUpdate,
        actor: User,
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
        actor: User,
        hard_delete: bool = False,
    ) -> None:
        """Elimina una empresa de forma lógica o permanente."""
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException(
                "Solo un SUPERADMIN puede realizar un borrado permanente.",
                403,
            )

        business = await BusinessService.get_business(repository, business_id)

        if actor.role not in {Role.SUPERADMIN, Role.ADMIN} and actor.id != business.owner_id:
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
