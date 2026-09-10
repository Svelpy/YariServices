from beanie import PydanticObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)

from app.core.repositories import BaseRepository
from app.shared.enums import Action, Module
from app.domains.auth import CurrentUser
from app.domains.auth.dependencies import (
    require_platform_permission,
    require_tenant_permission,
)
from app.domains.stores.dependencies import get_store_repository
from app.domains.stores.models import Store
from app.domains.stores.schemas import (
    StoreMeUpdate,
    StoreResponse,
    StoreResponseAudit,
    StoreUpdate,
    StorefrontResponse,
    StorefrontResponseAudit
)
from app.domains.stores.services import StoreService

from app.domains.meta import Meta
from app.domains.meta.dependencies import get_meta_repository



router = APIRouter(prefix="/stores", tags=["Stores Management"])



@router.get("/me", response_model=StorefrontResponse)
async def get_my_storefront(
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.READ)),
    store_repository: BaseRepository[Store] = Depends(get_store_repository),
    meta_repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Obtiene el negocio y Meta del tenant autenticado."""
    return await StoreService.get_storefront(
        store_repository=store_repository,
        meta_repository=meta_repository,
        store_id=current_user.store_id,
    )


@router.patch("/me", response_model=StoreResponse)
async def update_my_store(
    update_data: StoreMeUpdate,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.STORES, Action.UPDATE)),
    repository: BaseRepository[Store] = Depends(get_store_repository),
):
    """Actualiza el perfil editable de la empresa del usuario autenticado."""
    return await StoreService.update_my_store(
        repository=repository,
        update_data=update_data,
        actor=current_user,
    )



@router.put("/me/logo", response_model=StoreResponse)
async def update_my_store_logo(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_tenant_permission(Module.STORES, Action.UPDATE)),
    repository: BaseRepository[Store] = Depends(get_store_repository),
):
    """Sube o reemplaza el logo del negocio del usuario autenticado."""
    return await StoreService.update_my_store_logo(
        repository=repository,
        file=file,
        actor=current_user,
    )


@router.get("/{store_id}", response_model=StorefrontResponseAudit)
async def get_storefront(
    store_id: PydanticObjectId,
    _: CurrentUser = Depends(require_platform_permission(Module.META, Action.READ)),
    store_repository: BaseRepository[Store] = Depends(get_store_repository),
    meta_repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Obtiene el negocio y Meta por ID desde la plataforma."""
    return await StoreService.get_storefront(
        store_repository=store_repository,
        meta_repository=meta_repository,
        store_id=store_id,
    )


@router.patch("/{store_id}", response_model=StoreResponseAudit)
async def update_store(
    store_id: PydanticObjectId,
    update_data: StoreUpdate,
    current_user: CurrentUser = Depends(require_platform_permission(Module.STORES, Action.UPDATE)),
    repository: BaseRepository[Store] = Depends(get_store_repository),
):
    """Actualiza los datos administrativos de una empresa."""
    return await StoreService.update_store(
        repository=repository,
        store_id=store_id,
        update_data=update_data,
        actor=current_user,
    )


@router.put("/{store_id}/logo", response_model=StoreResponseAudit)
async def update_store_logo(
    store_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_platform_permission(Module.STORES, Action.UPDATE)),
    repository: BaseRepository[Store] = Depends(get_store_repository),
):
    """Sube o reemplaza el logo de un negocio desde la plataforma."""
    return await StoreService.update_store_logo(
        repository=repository,
        store_id=store_id,
        file=file,
        actor=current_user,
    )


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_store(
    store_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: CurrentUser = Depends(require_platform_permission(Module.STORES, Action.DELETE)),
    repository: BaseRepository[Store] = Depends(get_store_repository),
):
    """Elimina una empresa desde la plataforma."""
    await StoreService.delete_store(
        repository=repository,
        store_id=store_id,
        actor=current_user,
        hard_delete=hard_delete,
    )
    return None





