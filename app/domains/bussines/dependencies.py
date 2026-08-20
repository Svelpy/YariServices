from app.core.repositories import BaseRepository
from app.domains.bussines.models import Business


def get_business_repository() -> BaseRepository[Business]:
    """Repositorio global para consultar negocios desde sus dependencias."""
    return BaseRepository(Business)
