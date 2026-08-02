from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.shared.enums import Action, Module
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth.dependencies import (
    get_current_business_id,
    require_permission,
)
from app.domains.products import (
    ProductCreate,
    ProductResponse,
    ProductResponseAudit,
    ProductService,
    ProductUpdate,
)
from app.domains.users import User

router = APIRouter(prefix="/products", tags=["Products Management"])


@router.post("", response_model=ProductResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.CREATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Crea un nuevo producto en el catálogo de la empresa.
    """
    return await ProductService.create_product(
        product_data=product_data,
        actor_id=current_user.id,
        business_id=business_id,
    )


@router.get("", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None, description="Búsqueda por nombre, slug, barcode, sku, marca o descripción"),
    category_id: PydanticObjectId | None = Query(None, description="Filtrar por categoría"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo/inactivo"),
    _: User = Depends(require_permission(Module.PRODUCTS, Action.READ)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Lista productos de la empresa con filtros y paginación.
    """
    return await ProductService.list_products(
        business_id=business_id,
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
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Obtiene los detalles de un producto por su slug.
    """
    return await ProductService.get_product_by_slug(slug=slug, business_id=business_id)


@router.get("/{product_id}", response_model=ProductResponseAudit)
async def get_product(
    product_id: PydanticObjectId,
    _: User = Depends(require_permission(Module.PRODUCTS, Action.READ)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Obtiene los detalles de un producto por su ID.
    """
    return await ProductService.get_product(product_id=product_id, business_id=business_id)


@router.patch("/{product_id}", response_model=ProductResponseAudit)
async def update_product(
    product_id: PydanticObjectId,
    update_data: ProductUpdate,
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.UPDATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Actualiza la información de un producto.
    """
    return await ProductService.update_product(
        product_id=product_id,
        update_data=update_data,
        actor_id=current_user.id,
        business_id=business_id,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.DELETE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Elimina un producto del catálogo.
    """
    await ProductService.delete_product(
        product_id=product_id,
        actor=current_user,
        business_id=business_id,
        hard_delete=hard_delete,
    )
    return None


@router.post("/{product_id}/images", response_model=ProductResponseAudit)
async def upload_product_image(
    product_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.UPDATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Sube una imagen para el producto a Cloudinary y la añade a su galería de imágenes.
    """
    return await ProductService.upload_image(
        product_id=product_id,
        file=file,
        actor_id=current_user.id,
        business_id=business_id,
    )


@router.delete("/{product_id}/images", response_model=ProductResponseAudit)
async def delete_product_image(
    product_id: PydanticObjectId,
    image_url: str = Query(..., description="URL de Cloudinary de la imagen a eliminar"),
    current_user: User = Depends(require_permission(Module.PRODUCTS, Action.UPDATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Elimina una imagen específica de la galería del producto y de Cloudinary.
    """
    return await ProductService.delete_image(
        product_id=product_id,
        image_url=image_url,
        actor_id=current_user.id,
        business_id=business_id,
    )
