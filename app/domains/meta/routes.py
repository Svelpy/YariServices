from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.core.repositories import BaseRepository
from app.shared.enums import Action, Module
from app.domains.auth import CurrentUser
from app.domains.auth.dependencies import (
    require_platform_permission,
    require_tenant_permission,
)
from app.domains.meta.dependencies import get_meta_repository
from app.domains.meta.models import Meta
from app.domains.meta.schemas import (
    MetaMeUpdate,
    MetaResponse,
    MetaResponseAudit,
    MetaUpdate,
)
from app.domains.meta.services import MetaService


router = APIRouter(prefix="/meta", tags=["Storefront Meta Management"])


@router.get("/me", response_model=MetaResponse)
async def get_my_meta(
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.READ)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Obtiene la configuración del storefront del negocio autenticado."""
    return await MetaService.get_meta(repository=repository,business_id=current_user.business_id)


@router.patch("/me", response_model=MetaResponse)
async def update_my_meta(
    update_data: MetaMeUpdate,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Actualiza los campos editables del storefront autenticado."""
    return await MetaService.update_meta(
        repository=repository,
        business_id=current_user.business_id,
        update_data=update_data,
        actor=current_user,
    )


@router.put("/me/og-image", response_model=MetaResponse)
async def replace_my_og_image(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Sube o reemplaza la imagen Open Graph del storefront autenticado."""
    return await MetaService.replace_og_image(
        repository=repository,
        business_id=current_user.business_id,
        file=file,
        actor=current_user,
    )


@router.put("/me/favicon", response_model=MetaResponse)
async def replace_my_favicon(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Sube o reemplaza el favicon del storefront autenticado."""
    return await MetaService.replace_favicon(
        repository=repository,
        business_id=current_user.business_id,
        file=file,
        actor=current_user,
    )


@router.post("/me/carousel-images",response_model=MetaResponse,status_code=status.HTTP_201_CREATED,)
async def add_my_carousel_image(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Agrega una imagen al carrusel del storefront autenticado."""
    return await MetaService.add_carousel_image(
        repository=repository,
        business_id=current_user.business_id,
        file=file,
        actor=current_user,
    )


@router.delete("/me/carousel-images", response_model=MetaResponse)
async def delete_my_carousel_image(
    image_url: str = Query(..., min_length=1, max_length=2048,description="URL de la imagen del carrusel que se eliminará"),
    current_user: CurrentUser = Depends(require_tenant_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Elimina una imagen del carrusel del storefront autenticado."""
    return await MetaService.delete_carousel_image(
        repository=repository,
        business_id=current_user.business_id,
        image_url=image_url,
        actor=current_user,
    )


@router.get("/{business_id}", response_model=MetaResponseAudit)
async def get_meta(
    business_id: PydanticObjectId,
    _: CurrentUser = Depends(require_platform_permission(Module.META, Action.READ)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Obtiene la configuración de un storefront desde la plataforma."""
    return await MetaService.get_meta(repository=repository,business_id=business_id)


@router.patch("/{business_id}", response_model=MetaResponseAudit)
async def update_meta(
    business_id: PydanticObjectId,
    update_data: MetaUpdate,
    current_user: CurrentUser = Depends(require_platform_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Actualiza administrativamente la configuración de un storefront."""
    return await MetaService.update_meta(
        repository=repository,
        business_id=business_id,
        update_data=update_data,
        actor=current_user,
    )


@router.put("/{business_id}/og-image", response_model=MetaResponseAudit)
async def replace_og_image(
    business_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_platform_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Sube o reemplaza la imagen Open Graph desde la plataforma."""
    return await MetaService.replace_og_image(
        repository=repository,
        business_id=business_id,
        file=file,
        actor=current_user,
    )


@router.put("/{business_id}/favicon", response_model=MetaResponseAudit)
async def replace_favicon(
    business_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_platform_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Sube o reemplaza el favicon desde la plataforma."""
    return await MetaService.replace_favicon(
        repository=repository,
        business_id=business_id,
        file=file,
        actor=current_user,
    )


@router.post("/{business_id}/carousel-images",response_model=MetaResponseAudit,status_code=status.HTTP_201_CREATED,)
async def add_carousel_image(
    business_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_platform_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Agrega una imagen al carrusel desde la plataforma."""
    return await MetaService.add_carousel_image(
        repository=repository,
        business_id=business_id,
        file=file,
        actor=current_user,
    )


@router.delete("/{business_id}/carousel-images",response_model=MetaResponseAudit)
async def delete_carousel_image(
    business_id: PydanticObjectId,
    image_url: str = Query(...,min_length=1,max_length=2048,description="URL de la imagen del carrusel que se eliminará"),
    current_user: CurrentUser = Depends(require_platform_permission(Module.META, Action.UPDATE)),
    repository: BaseRepository[Meta] = Depends(get_meta_repository),
):
    """Elimina una imagen del carrusel desde la plataforma."""
    return await MetaService.delete_carousel_image(
        repository=repository,
        business_id=business_id,
        image_url=image_url,
        actor=current_user,
    )
