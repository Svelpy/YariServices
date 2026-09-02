from beanie import PydanticObjectId
from fastapi import UploadFile, status

from app.core.repositories import BaseRepository
from app.shared.errors.codes import ErrorCode
from app.shared.errors.exceptions import AppException
from app.integrations.cloudinary import CloudinaryService
from app.domains.auth import CurrentUser
from app.domains.meta.models import Meta, ThemeColors
from app.domains.meta.schemas import MetaMeUpdate, MetaUpdate

class MetaService:
    """Gestiona la configuración y los recursos visuales del storefront."""

    @staticmethod
    async def get_meta(repository: BaseRepository[Meta], business_id: PydanticObjectId,) -> Meta:
        meta = await repository.find_one({"business_id": business_id,"is_deleted": False})
        if meta is None:
            raise AppException("Configuración del storefront no encontrada.",status.HTTP_404_NOT_FOUND,ErrorCode.RESOURCE_NOT_FOUND)
        return meta

    @staticmethod
    async def update_meta(
        repository: BaseRepository[Meta],
        business_id: PydanticObjectId,
        update_data: MetaUpdate | MetaMeUpdate,
        actor: CurrentUser,
    ) -> Meta:
        meta = await MetaService.get_meta(repository, business_id)
        update_dict = update_data.model_dump(exclude_unset=True)
        custom_domain = update_dict.get("custom_domain")
        if custom_domain is not None:
            existing_domain = await repository.find_one(
                    {
                        "custom_domain": custom_domain,
                        "_id": {"$ne": meta.id},
                        "is_deleted": False,
                    }
                )
            if existing_domain:
                raise AppException("El dominio personalizado ya está en uso.",status.HTTP_409_CONFLICT,ErrorCode.CONFLICT,)

        
        if "colors" in update_dict:
            update_dict["colors"] = ThemeColors.model_validate(update_dict["colors"])
        for field_name, value in update_dict.items():
            setattr(meta, field_name, value)
        meta.updated_by = actor.id
        return await repository.save(meta)
 
    
    @staticmethod
    async def replace_og_image(
        repository: BaseRepository[Meta],
        business_id: PydanticObjectId,
        file: UploadFile,
        actor: CurrentUser,
    ) -> Meta:
        meta = await MetaService.get_meta(repository, business_id)
        old_og = meta.og_image_url
        new_og = await CloudinaryService.upload_image(file,folder=f"businesses/{meta.business_id}/og-images")
        meta.og_image_url = new_og
        meta.updated_by = actor.id
        meta = await repository.save(meta)

        if old_og:
            await CloudinaryService.safe_delete_image(old_og)

        return meta

    @staticmethod
    async def replace_favicon(
        repository: BaseRepository[Meta],
        business_id: PydanticObjectId,
        file: UploadFile,
        actor: CurrentUser,
    ) -> Meta:
        meta = await MetaService.get_meta(repository, business_id)
        old_favicon = meta.favicon_url
        new_favicon = await CloudinaryService.upload_image(file,folder=f"businesses/{meta.business_id}/favicon")
        meta.favicon_url = new_favicon
        meta.updated_by = actor.id
        meta = await repository.save(meta)

        if old_favicon:
            await CloudinaryService.safe_delete_image(old_favicon)

        return meta

    @staticmethod
    async def add_carousel_image(
        repository: BaseRepository[Meta],
        business_id: PydanticObjectId,
        file: UploadFile,
        actor: CurrentUser,
    ) -> Meta:
        meta = await MetaService.get_meta(repository, business_id)
        image_url = await CloudinaryService.upload_image(file,folder=f"businesses/{meta.business_id}/carousel")
        meta.carousel_urls.append(image_url)
        meta.updated_by = actor.id
        return await repository.save(meta)


    @staticmethod
    async def delete_carousel_image(
        repository: BaseRepository[Meta],
        business_id: PydanticObjectId,
        image_url: str,
        actor: CurrentUser,
    ) -> Meta:
        meta = await MetaService.get_meta(repository, business_id)
        if image_url not in meta.carousel_urls:
            raise AppException("La imagen no pertenece al carrusel del storefront.",status.HTTP_404_NOT_FOUND,ErrorCode.RESOURCE_NOT_FOUND)
        meta.carousel_urls.remove(image_url)
        meta.updated_by = actor.id
        saved_meta = await repository.save(meta)
 

        await CloudinaryService.delete_image(image_url)
        return saved_meta
