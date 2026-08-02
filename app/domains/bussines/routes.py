from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.shared.enums import Action, Module
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth.dependencies import (
    get_current_user,
    require_permission,
)
from app.domains.bussines import (
    BusinessCreate,
    BusinessResponse,
    BusinessResponseAudit,
    BusinessService,
    BusinessUpdate,
)
from app.domains.users import User

router = APIRouter(prefix="/businesses", tags=["Business Management"])


@router.post("", response_model=BusinessResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_business(
    data: BusinessCreate,
    current_user: User = Depends(require_permission(Module.BUSINESS, Action.CREATE)),
):
    """
    Registra una nueva empresa y la asigna al propietario especificado (Acción Administrativa).
    """
    return await BusinessService.create_business(data=data, actor=current_user)


@router.get("", response_model=PaginatedResponse[BusinessResponseAudit])
async def list_businesses(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None, description="Búsqueda de texto en nombre o slug"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    _: User = Depends(require_permission(Module.BUSINESS, Action.READ)),
):
    """
    Lista empresas registradas con filtros y paginación (Acción Administrativa).
    """
    return await BusinessService.list_businesses(
        page=page,
        per_page=per_page,
        q=q,
        is_active=is_active,
    )


@router.get("/me", response_model=BusinessResponse)
async def get_my_business(
    current_user: User = Depends(get_current_user),
):
    """
    Obtiene la información de la empresa a la que pertenece el usuario autenticado.
    """
    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene una empresa asignada",
        )
    return await BusinessService.get_business(business_id=current_user.business_id)


@router.get("/slug/{slug}", response_model=BusinessResponse)
async def get_business_by_slug(slug: str):
    """
    Obtiene los datos públicos de una empresa por su slug.
    """
    return await BusinessService.get_business_by_slug(slug=slug)


@router.get("/{business_id}", response_model=BusinessResponseAudit)
async def get_business(
    business_id: PydanticObjectId,
    _: User = Depends(require_permission(Module.BUSINESS, Action.READ)),
):
    """
    Obtiene los detalles de una empresa por su ID (Acción Administrativa).
    """
    return await BusinessService.get_business(business_id=business_id)


@router.patch("/{business_id}", response_model=BusinessResponseAudit)
async def update_business(
    business_id: PydanticObjectId,
    update_data: BusinessUpdate,
    current_user: User = Depends(require_permission(Module.BUSINESS, Action.UPDATE)),
):
    """
    Actualiza los datos de una empresa (Acción Administrativa).
    """
    return await BusinessService.update_business(
        business_id=business_id,
        update_data=update_data,
        actor=current_user,
    )


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: User = Depends(require_permission(Module.BUSINESS, Action.DELETE)),
):
    """
    Elimina una empresa (Acción Administrativa).
    """
    await BusinessService.delete_business(
        business_id=business_id,
        actor=current_user,
        hard_delete=hard_delete,
    )
    return None
