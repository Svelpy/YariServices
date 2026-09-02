from beanie import PydanticObjectId
from fastapi import APIRouter, Depends

from app.core.repositories import BaseRepository
from app.shared.enums import Action, Module
from app.domains.auth import CurrentUser
from app.domains.auth.dependencies import (
    require_platform_permission,
    require_tenant_permission,
)
from app.domains.bussines import Business
from app.domains.bussines.dependencies import get_business_repository
from app.domains.meta import Meta
from app.domains.meta.dependencies import get_meta_repository
from app.domains.store.schemas import StoreResponse, StoreResponseAudit
from app.domains.store.services import StoreService


router = APIRouter(prefix="/stores", tags=["Store Management"])


@router.get("/me", response_model=StoreResponse)
async def get_my_store(
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.READ)),
    business_repository: BaseRepository[Business] = Depends(get_business_repository),
    meta_repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Obtiene el negocio y Meta del tenant autenticado."""
    return await StoreService.get_store(
        business_repository=business_repository,
        meta_repository=meta_repository,
        business_id=current_user.business_id,
    )


@router.get("/{business_id}", response_model=StoreResponseAudit)
async def get_store(
    business_id: PydanticObjectId,
    _: CurrentUser = Depends(require_platform_permission(Module.META, Action.READ)),
    business_repository: BaseRepository[Business] = Depends(get_business_repository),
    meta_repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Obtiene el negocio y Meta por ID desde la plataforma."""
    return await StoreService.get_store(
        business_repository=business_repository,
        meta_repository=meta_repository,
        business_id=business_id,
    )
