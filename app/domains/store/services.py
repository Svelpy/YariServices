import asyncio
from typing import TypedDict

from beanie import PydanticObjectId

from app.core.repositories import BaseRepository
from app.domains.bussines import Business, BusinessService
from app.domains.meta import Meta, MetaService


class Store(TypedDict):
    business: Business
    meta: Meta


class StoreService:
    """Compone los recursos necesarios para representar una tienda."""

    @staticmethod
    async def get_store(
        business_repository: BaseRepository[Business],
        meta_repository: BaseRepository[Meta],
        business_id: PydanticObjectId,
    ) -> Store:
        business, meta = await asyncio.gather(
            BusinessService.get_business(
                repository=business_repository,
                business_id=business_id,
            ),
            MetaService.get_meta(
                repository=meta_repository,
                business_id=business_id,
            ),
        )
        return {"business": business, "meta": meta}
