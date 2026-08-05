from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.repositories import TenantRepository
from app.shared.enums import Action, Module
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth.dependencies import create_repo, require_permission
from app.domains.products.models import Product
from app.domains.products.schemas import (
    ProductCreate,
    ProductResponse,
    ProductResponseAudit,
    ProductUpdate,
)
from app.domains.products.services import ProductService
from app.domains.users import User


router = APIRouter(prefix="/products", tags=["Products Management"])
get_product_repository = create_repo(Product)


@router.post("", response_model=ProductResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.CREATE)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Crea un nuevo producto en el catálogo del tenant autorizado."""
    return await ProductService.create_product(
        repository=repo,
        product_data=product_data,
        actor_id=current_user.id,
    )


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(
        None,
        description="Búsqueda por nombre, slug, barcode, sku, marca o descripción",
    ),
    category_id: PydanticObjectId | None = Query(None, description="Filtrar por categoría"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    _: User = Depends(require_permission(Module.PRODUCTS, Action.READ)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Lista productos con filtros y paginación dentro del tenant autorizado."""
    return await ProductService.list_products(
        repository=repo,
        page=page,
        per_page=per_page,
        q=q,
        category_id=category_id,
        is_active=is_active,
    )


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
    slug: str,
    _: User = Depends(require_permission(Module.PRODUCTS, Action.READ)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Obtiene un producto por slug dentro del tenant autorizado."""
    return await ProductService.get_product_by_slug(repository=repo, slug=slug)


@router.get("/{product_id}", response_model=ProductResponseAudit)
async def get_product(
    product_id: PydanticObjectId,
    _: User = Depends(require_permission(Module.PRODUCTS, Action.READ)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Obtiene un producto por ID dentro del tenant autorizado."""
    return await ProductService.get_product(repository=repo, product_id=product_id)


@router.patch("/{product_id}", response_model=ProductResponseAudit)
async def update_product(
    product_id: PydanticObjectId,
    update_data: ProductUpdate,
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.UPDATE)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Actualiza la información de un producto dentro del tenant autorizado."""
    return await ProductService.update_product(
        repository=repo,
        product_id=product_id,
        update_data=update_data,
        actor_id=current_user.id,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.DELETE)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Elimina un producto dentro del tenant autorizado."""
    await ProductService.delete_product(
        repository=repo,
        product_id=product_id,
        actor=current_user,
        hard_delete=hard_delete,
    )
    return None


@router.post("/{product_id}/images", response_model=ProductResponseAudit)
async def upload_product_image(
    product_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.UPDATE)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Sube una imagen para un producto del tenant autorizado."""
    return await ProductService.upload_image(
        repository=repo,
        product_id=product_id,
        file=file,
        actor_id=current_user.id,
    )


@router.delete("/{product_id}/images", response_model=ProductResponseAudit)
async def delete_product_image(
    product_id: PydanticObjectId,
    image_url: str = Query(..., description="URL de Cloudinary de la imagen a eliminar"),
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.UPDATE)),
    repo: TenantRepository[Product] = Depends(get_product_repository),
):
    """Elimina una imagen de un producto del tenant autorizado."""
    return await ProductService.delete_image(
        repository=repo,
        product_id=product_id,
        image_url=image_url,
        actor_id=current_user.id,
    )
