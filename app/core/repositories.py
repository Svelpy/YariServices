from typing import Any, Generic, TypeVar

from beanie import Document, PydanticObjectId


ModelType = TypeVar("ModelType", bound=Document)


class BaseRepository(Generic[ModelType]):
    """Operaciones genéricas de persistencia para documentos Beanie."""

    def __init__(self, model: type[ModelType]):
        self.model = model

    @staticmethod
    def _build_filters(filters: dict[str, Any] | None = None) -> dict[str, Any]:
        return dict(filters or {})

    async def get(self, doc_id: PydanticObjectId) -> ModelType | None:
        return await self.find_one({"_id": doc_id})

    async def find_one(self, filters: dict[str, Any]) -> ModelType | None:
        return await self.model.find_one(self._build_filters(filters))

    async def list(self,filters: dict[str, Any] | None = None,*,
        skip: int = 0,
        limit: int | None = None,
        sort: tuple[Any, ...] | None = None,
    ) -> list[ModelType]:
        
        query = self.model.find(self._build_filters(filters))
        if sort:
            query = query.sort(*sort)
        if skip:
            query = query.skip(skip)
        if limit is not None:
            query = query.limit(limit)

        return await query.to_list()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        return await self.model.find(self._build_filters(filters)).count()

    async def create(self, document: ModelType) -> ModelType:
        await document.save()
        return document

    async def save(self, document: ModelType) -> ModelType:
        await document.save()
        return document

    async def delete(self, document: ModelType) -> None:
        await document.delete()


class TenantRepository(BaseRepository[ModelType], Generic[ModelType]):
    """Repositorio genérico que agrega business_id a todas las consultas."""

    def __init__(
        self,
        model: type[ModelType],
        business_id: PydanticObjectId,
    ):
        super().__init__(model)
        self.business_id = business_id

    def _build_filters(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        tenant_filters = super()._build_filters(filters)
        tenant_filters["business_id"] = self.business_id
        return tenant_filters

    async def create(self, document: ModelType) -> ModelType:
        setattr(document, "business_id", self.business_id)
        return await super().create(document)

    async def save(self, document: ModelType) -> ModelType:
        if getattr(document, "business_id", None) != self.business_id:
            raise ValueError("El documento no pertenece a este business_id")

        return await super().save(document)

    async def delete(self, document: ModelType) -> None:
        if getattr(document, "business_id", None) != self.business_id:
            raise ValueError("El documento no pertenece a este business_id")

        await super().delete(document)

