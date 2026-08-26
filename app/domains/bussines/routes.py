from beanie import PydanticObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from app.core.repositories import BaseRepository
from app.shared.enums import Action, Module
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth import CurrentUser
from app.domains.auth.dependencies import (
    require_platform_permission,
    require_tenant_permission,
)
from app.domains.bussines.dependencies import get_business_repository
from app.domains.bussines.models import Business
from app.domains.bussines.schemas import (
    BusinessMeUpdate,
    BusinessResponse,
    BusinessResponseAudit,
    BusinessUpdate,
)
from app.domains.bussines.services import BusinessService



router = APIRouter(prefix="/businesses", tags=["Business Management"])



@router.get("", response_model=PaginatedResponse[BusinessResponseAudit])
async def list_businesses(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None, description="Búsqueda de texto en nombre o slug"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    _: CurrentUser= Depends(require_platform_permission(Module.BUSINESS, Action.READ)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Lista empresas registradas desde la plataforma."""
    return await BusinessService.list_businesses(
        repository=repository,
        page=page,
        per_page=per_page,
        q=q,
        is_active=is_active,
    )


@router.get("/me", response_model=BusinessResponse)
async def get_my_business(
    current_user: CurrentUser = Depends(require_tenant_permission(Module.BUSINESS, Action.READ)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Obtiene la empresa asociada al usuario autenticado."""
    if current_user.business_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="El usuario no tiene una empresa asignada")

    return await BusinessService.get_business(repository=repository,business_id=current_user.business_id)


@router.patch("/me", response_model=BusinessResponse)
async def update_my_business(
    update_data: BusinessMeUpdate,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.BUSINESS, Action.UPDATE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Actualiza el perfil editable de la empresa del usuario autenticado."""
    return await BusinessService.update_my_business(
        repository=repository,
        update_data=update_data,
        actor=current_user,
    )



@router.put("/me/logo", response_model=BusinessResponse)
async def update_my_business_logo(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_tenant_permission(Module.BUSINESS, Action.UPDATE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Sube o reemplaza el logo del negocio del usuario autenticado."""
    return await BusinessService.update_my_business_logo(
        repository=repository,
        file=file,
        actor=current_user,
    )


@router.get("/{business_id}", response_model=BusinessResponseAudit)
async def get_business(
    business_id: PydanticObjectId,
    _: CurrentUser= Depends(require_platform_permission(Module.BUSINESS, Action.READ)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Obtiene los detalles de una empresa desde la plataforma."""
    return await BusinessService.get_business(
        repository=repository,
        business_id=business_id,
    )


@router.patch("/{business_id}", response_model=BusinessResponseAudit)
async def update_business(
    business_id: PydanticObjectId,
    update_data: BusinessUpdate,
    current_user: CurrentUser = Depends(require_platform_permission(Module.BUSINESS, Action.UPDATE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Actualiza los datos administrativos de una empresa."""
    return await BusinessService.update_business(
        repository=repository,
        business_id=business_id,
        update_data=update_data,
        actor=current_user,
    )


@router.put("/{business_id}/logo", response_model=BusinessResponseAudit)
async def update_business_logo(
    business_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_platform_permission(Module.BUSINESS, Action.UPDATE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Sube o reemplaza el logo de un negocio desde la plataforma."""
    return await BusinessService.update_business_logo(
        repository=repository,
        business_id=business_id,
        file=file,
        actor=current_user,
    )


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: CurrentUser = Depends(require_platform_permission(Module.BUSINESS, Action.DELETE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Elimina una empresa desde la plataforma."""
    await BusinessService.delete_business(
        repository=repository,
        business_id=business_id,
        actor=current_user,
        hard_delete=hard_delete,
    )
    return None
