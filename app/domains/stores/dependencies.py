from app.core.repositories import BaseRepository
from app.domains.stores.models import Store


def get_store_repository() -> BaseRepository[Store]:
    """Repositorio global para consultar negocios desde sus dependencias."""
    return BaseRepository(Store)
