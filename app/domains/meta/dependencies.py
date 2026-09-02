from app.core.repositories import BaseRepository
from app.domains.meta.models import Meta


def get_meta_repository() -> BaseRepository[Meta]:
    """Construye el repositorio global de configuración de storefront."""
    return BaseRepository(Meta)
