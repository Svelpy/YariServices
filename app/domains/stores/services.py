import math
import re
from datetime import datetime, timezone
from typing import Any, TypedDict
import asyncio

from beanie import PydanticObjectId
from fastapi import UploadFile

from app.core.repositories import BaseRepository
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug
from app.integrations.cloudinary import CloudinaryService
from app.domains.auth import CurrentUser
from app.domains.stores.models import Store
from app.domains.stores.schemas import StoreMeUpdate, StoreUpdate
from app.domains.meta import Meta, MetaService

class Storefront(TypedDict):
    store: Store
    meta: Meta
class StoreService:

    @staticmethod
    async def get_store(repository: BaseRepository[Store],store_id: PydanticObjectId) -> Store:
        store = await repository.get(store_id)
        if not store or store.is_deleted:
            raise AppException("Empresa no existente.", 404)
        return store

    @staticmethod
    async def list_store(
        repository: BaseRepository[Store],
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
        stores = await repository.list(
            filters,
            skip=skip,
            limit=per_page,
            sort=(+Store.created_at,),
        )

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total_count / per_page) if per_page > 0 else 0,
            "data": stores,
        }

    @staticmethod
    async def update_store(
        repository: BaseRepository[Store],
        store_id: PydanticObjectId,
        update_data: StoreUpdate | StoreMeUpdate,
        actor: CurrentUser,
    ) -> Store:
        """Actualiza una empresa respetando los permisos del actor."""
        store = await StoreService.get_store(repository, store_id)

        update_dict = update_data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"] != store.name:
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException("El nombre proporcionado no genera un slug válido.",400)

            existing_slug = await repository.find_one(
                {
                    "slug": new_slug,
                    "_id": {"$ne": store.id},
                    "is_deleted": False,
                }
            )
            if existing_slug:
                raise AppException(f"El slug '{new_slug}' ya está registrado para otra empresa.",409)
            update_dict["slug"] = new_slug

        for key, value in update_dict.items():
            setattr(store, key, value)

        store.updated_by = actor.id
        return await repository.save(store)

    @staticmethod
    async def update_my_store(
        repository: BaseRepository[Store],
        update_data: StoreMeUpdate,
        actor: CurrentUser,
    ) -> Store:
        """Actualiza el negocio propio del usuario autenticado."""
        if actor.store_id is None:
            raise AppException("El usuario no tiene una empresa asignada.", 404)

        return await StoreService.update_store(
            repository=repository,
            store_id=actor.store_id,
            update_data=update_data,
            actor=actor,
        )

    @staticmethod
    async def delete_store(
        repository: BaseRepository[Store],
        store_id: PydanticObjectId,
        actor: CurrentUser,
        hard_delete: bool = False,
    ) -> None:
        """Elimina una empresa de forma lógica o permanente."""
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException("Solo un SUPERADMIN puede realizar un borrado permanente.",403)

        store = await StoreService.get_store(repository, store_id)

        if actor.role not in {Role.SUPERADMIN, Role.ADMIN}:
            raise AppException("No tienes permisos para eliminar esta empresa.", 403)

        if hard_delete:
            await repository.delete(store)
            return

        now = datetime.now(timezone.utc)
        store.is_deleted = True
        store.deleted_at = now
        store.deleted_by = actor.id
        store.updated_by = actor.id
        await repository.save(store)

    @staticmethod
    async def update_store_logo(
        repository: BaseRepository[Store],
        store_id: PydanticObjectId,
        file: UploadFile,
        actor: CurrentUser,
    ) -> Store:
        store = await StoreService.get_store(repository, store_id)

        old_logo_url = store.logo_url
        new_logo_url = await CloudinaryService.upload_image(
            file,
            folder="stores",
        )

        store.logo_url = new_logo_url
        store.updated_by = actor.id

        store = await repository.save(store)

        if old_logo_url:
            await CloudinaryService.safe_delete_image(old_logo_url)

        return store

    @staticmethod
    async def update_my_store_logo(
        repository: BaseRepository[Store],
        file: UploadFile,
        actor: CurrentUser,
    ) -> Store:
        if actor.store_id is None:
            raise AppException("El usuario no tiene una empresa asignada.", 404)

        return await StoreService.update_store_logo(
            repository=repository,
            store_id=actor.store_id,
            file=file,
            actor=actor,
        )


    @staticmethod
    async def get_storefront(
        store_repository: BaseRepository[Store],
        meta_repository: BaseRepository[Meta],
        store_id: PydanticObjectId,
    ) -> Storefront:
        store, meta = await asyncio.gather(
            StoreService.get_store(
                repository=store_repository,
                store_id=store_id,
            ),
            MetaService.get_meta(
                repository=meta_repository,
                store_id=store_id,
            ),
        )
        return {"store": store, "meta": meta}
