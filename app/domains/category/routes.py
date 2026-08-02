from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.shared.enums import Action, Module
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.schemas.tree import TreeResponse
from app.domains.auth.dependencies import (
    get_current_business_id,
    require_permission,
)
from app.domains.category.schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryResponseAudit,
    CategoryUpdate,
)
from app.domains.category.services import CategoryService
from app.domains.users import User

router = APIRouter(prefix="/categories", tags=["Categories Management"])


@router.get("/tree", response_model=TreeResponse[CategoryResponse])
async def get_categories_tree(
    _: User = Depends(require_permission(Module.CATEGORY, Action.READ)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Retorna el árbol jerárquico completo de categorías activas de la empresa.
    """
    return await CategoryService.get_categories_tree(business_id=business_id)


@router.get("", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None, description="Búsqueda de texto en nombre, slug o descripción"),
    parent_id: PydanticObjectId | None = Query(None, description="Filtrar por ID de la categoría padre ('null' para raíz)"),
    _: User = Depends(require_permission(Module.CATEGORY, Action.READ)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Lista las categorías de una empresa con filtros y paginación.
    """
    return await CategoryService.list_categories(
        business_id=business_id,
        page=page,
        per_page=per_page,
        q=q,
        parent_id=parent_id,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: PydanticObjectId,
    _: User = Depends(require_permission(Module.CATEGORY, Action.READ)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Obtiene los detalles de una categoría por su ID.
    """
    return await CategoryService.get_category(category_id=category_id, business_id=business_id)


@router.post("", response_model=CategoryResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(require_permission(Module.CATEGORY, Action.CREATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Crea una nueva categoría para la empresa del usuario autenticado.
    """
    return await CategoryService.create_category(
        category_data=category_data,
        actor_id=current_user.id,
        business_id=business_id,
    )


@router.patch("/{category_id}", response_model=CategoryResponseAudit)
async def update_category(
    category_id: PydanticObjectId,
    update_data: CategoryUpdate,
    current_user: User = Depends(require_permission(Module.CATEGORY, Action.UPDATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Actualiza la información de una categoría.
    """
    return await CategoryService.update_category(
        category_id=category_id,
        update_data=update_data,
        actor_id=current_user.id,
        business_id=business_id,
    )


@router.post("/{category_id}/banner", response_model=CategoryResponseAudit)
async def update_category_banner(
    category_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(Module.CATEGORY, Action.UPDATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Sube o actualiza la imagen del banner de una categoría.
    """
    return await CategoryService.update_banner(
        category_id=category_id,
        file=file,
        actor_id=current_user.id,
        business_id=business_id,
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: User = Depends(require_permission(Module.CATEGORY, Action.DELETE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Realiza un borrado de una categoría y todos sus descendientes.
    """
    await CategoryService.delete_category(
        category_id=category_id,
        actor=current_user,
        business_id=business_id,
        hard_delete=hard_delete,
    )
    return None
