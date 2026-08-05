from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.repositories import BaseRepository
from app.shared.enums import Action, Module, Role
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth.dependencies import get_current_user, require_permission, require_roles
from app.domains.bussines.models import Business
from app.domains.bussines.schemas import (
    BusinessCreate,
    BusinessResponse,
    BusinessResponseAudit,
    BusinessMeUpdate,
    BusinessUpdate,
)
from app.domains.bussines.services import BusinessService
from app.domains.users.models import User


router = APIRouter(prefix="/businesses", tags=["Business Management"])


def get_business_repository() -> BaseRepository[Business]:
    return BaseRepository(Business)


def get_user_repository() -> BaseRepository[User]:
    return BaseRepository(User)


@router.post("", response_model=BusinessResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_business(
    data: BusinessCreate,
    current_user: User = Depends(require_permission(Module.BUSINESS, Action.CREATE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
    user_repository: BaseRepository[User] = Depends(get_user_repository),
):
    """Registra una nueva empresa desde la plataforma."""
    return await BusinessService.create_business(
        repository=repository,
        user_repository=user_repository,
        data=data,
        actor=current_user,
    )


@router.get("", response_model=PaginatedResponse[BusinessResponseAudit])
async def list_businesses(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None, description="Búsqueda de texto en nombre o slug"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    _: User = Depends(require_permission(Module.BUSINESS, Action.READ)),
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
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Obtiene la empresa asociada al usuario autenticado."""
    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene una empresa asignada",
        )

    return await BusinessService.get_business(
        repository=repository,
        business_id=current_user.business_id,
    )


@router.patch("/me", response_model=BusinessResponse)
async def update_my_business(
    update_data: BusinessMeUpdate,
    current_user: User = Depends(require_roles(Role.PROPIETARIO, Role.GERENTE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Actualiza el perfil editable de la empresa del usuario autenticado."""
    return await BusinessService.update_my_business(
        repository=repository,
        update_data=update_data,
        actor=current_user,
    )


@router.get("/slug/{slug}", response_model=BusinessResponse)
async def get_business_by_slug(
    slug: str,
    # Endpoint público: no requiere autenticación ni permisos.
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Obtiene los datos públicos de una empresa por su slug."""
    return await BusinessService.get_business_by_slug(
        repository=repository,
        slug=slug,
    )


@router.get("/{business_id}", response_model=BusinessResponseAudit)
async def get_business(
    business_id: PydanticObjectId,
    _: User = Depends(require_permission(Module.BUSINESS, Action.READ)),
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
    current_user: User = Depends(require_permission(Module.BUSINESS, Action.UPDATE)),
    repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Actualiza los datos administrativos de una empresa."""
    return await BusinessService.update_business(
        repository=repository,
        business_id=business_id,
        update_data=update_data,
        actor=current_user,
    )


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
    business_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: User = Depends(require_permission(Module.BUSINESS, Action.DELETE)),
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
