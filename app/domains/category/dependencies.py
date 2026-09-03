from fastapi import Depends

from app.core.repositories import TenantRepository
from app.shared.errors.exceptions import AppException
from app.shared.services.permissions import PLATFORM_ROLES
from app.domains.auth.dependencies import get_current_principal
from app.domains.auth.schemas import CurrentUser
from app.domains.category.models import Category


async def get_current_tenant_category_repository(current_user: CurrentUser = Depends(get_current_principal),) -> TenantRepository[Category]:
    """Repositorio de categorías limitado al negocio del usuario autenticado."""
    if current_user.role in PLATFORM_ROLES or current_user.business_id is None:
        raise AppException("El usuario no tiene un negocio tenant autorizado.",403)    
    return TenantRepository(Category, current_user.business_id)
