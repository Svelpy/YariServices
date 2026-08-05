import math
import re
from datetime import datetime, timezone
from typing import Any

from beanie import PydanticObjectId
from fastapi import UploadFile

from app.core.repositories import TenantRepository
from app.integrations.cloudinary import CloudinaryService
from app.domains.category.models import Category
from app.domains.products.models import Product, ProductAttribute
from app.domains.products.schemas import ProductCreate, ProductUpdate
from app.domains.users.models import User
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug


class ProductService:

    @staticmethod
    def _category_repository(
        repository: TenantRepository[Product],
    ) -> TenantRepository[Category]:
        return TenantRepository(Category, repository.business_id)

    @staticmethod
    async def create_product(
        repository: TenantRepository[Product],
        product_data: ProductCreate,
        actor_id: PydanticObjectId,
    ) -> Product:
        """Crea un producto dentro del tenant del repositorio."""
        slug = generate_slug(product_data.name)
        if not slug:
            raise AppException("El nombre del producto no genera un slug válido.", 400)

        existing_slug = await repository.find_one(
            {
                "slug": slug,
                "is_deleted": False,
            }
        )
        if existing_slug:
            raise AppException(
                f"El slug '{slug}' ya está registrado en otro producto activo de tu empresa.",
                409,
            )

        if product_data.barcode:
            existing_barcode = await repository.find_one(
                {
                    "barcode": product_data.barcode,
                    "is_deleted": False,
                }
            )
            if existing_barcode:
                raise AppException(
                    f"El código de barras '{product_data.barcode}' ya está registrado en tu empresa.",
                    409,
                )

        if product_data.sku:
            existing_sku = await repository.find_one(
                {
                    "sku": product_data.sku,
                    "is_deleted": False,
                }
            )
            if existing_sku:
                raise AppException(
                    f"El SKU '{product_data.sku}' ya está registrado en tu empresa.",
                    409,
                )

        if product_data.category_id:
            category = await ProductService._category_repository(repository).get(
                product_data.category_id
            )
            if not category or category.is_deleted:
                raise AppException(
                    "La categoría seleccionada no existe o no pertenece a tu empresa.",
                    404,
                )

        attribute_models = [
            ProductAttribute(key=attribute.key, value=attribute.value, label=attribute.label)
            for attribute in product_data.attributes
        ]

        product = Product(
            business_id=repository.business_id,
            name=product_data.name,
            slug=slug,
            barcode=product_data.barcode,
            sku=product_data.sku,
            presentation=product_data.presentation,
            category_id=product_data.category_id,
            brand=product_data.brand,
            description=product_data.description,
            price=product_data.price,
            price_discount=product_data.price_discount,
            stock=product_data.stock,
            min_stock=product_data.min_stock,
            images=product_data.images,
            display_order=product_data.display_order,
            attributes=attribute_models,
            is_active=product_data.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )

        return await repository.create(product)

    @staticmethod
    async def get_product(
        repository: TenantRepository[Product],
        product_id: PydanticObjectId,
    ) -> Product:
        """Obtiene un producto únicamente dentro del tenant del repositorio."""
        product = await repository.get(product_id)
        if not product or product.is_deleted:
            raise AppException("Producto no encontrado.", 404)

        return product

    @staticmethod
    async def get_product_by_slug(
        repository: TenantRepository[Product],
        slug: str,
    ) -> Product:
        """Obtiene un producto activo por slug dentro del tenant."""
        product = await repository.find_one(
            {
                "slug": slug,
                "is_deleted": False,
            }
        )
        if not product:
            raise AppException("Producto no encontrado.", 404)

        return product

    @staticmethod
    async def list_products(
        repository: TenantRepository[Product],
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        category_id: PydanticObjectId | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        """Lista productos aplicando filtros y paginación dentro del tenant."""
        filters: dict[str, Any] = {
            "is_deleted": False,
        }

        if category_id is not None:
            filters["category_id"] = category_id

        if is_active is not None:
            filters["is_active"] = is_active

        if q:
            safe_q = re.escape(q)
            filters["$or"] = [
                {"name": {"$regex": safe_q, "$options": "i"}},
                {"slug": {"$regex": safe_q, "$options": "i"}},
                {"barcode": {"$regex": safe_q, "$options": "i"}},
                {"sku": {"$regex": safe_q, "$options": "i"}},
                {"brand": {"$regex": safe_q, "$options": "i"}},
                {"description": {"$regex": safe_q, "$options": "i"}},
            ]

        total_count = await repository.count(filters)
        skip = (page - 1) * per_page
        products = await repository.list(
            filters,
            skip=skip,
            limit=per_page,
            sort=(+Product.name,),
        )

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total_count / per_page) if per_page > 0 else 0,
            "data": products,
        }

    @staticmethod
    async def update_product(
        repository: TenantRepository[Product],
        product_id: PydanticObjectId,
        update_data: ProductUpdate,
        actor_id: PydanticObjectId,
    ) -> Product:
        """Actualiza un producto dentro del tenant del repositorio."""
        product = await ProductService.get_product(repository, product_id)
        update_dict = update_data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"] != product.name:
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException(
                    "El nombre proporcionado no genera un slug válido.",
                    400,
                )

            existing_slug = await repository.find_one(
                {
                    "slug": new_slug,
                    "_id": {"$ne": product.id},
                    "is_deleted": False,
                }
            )
            if existing_slug:
                raise AppException(
                    f"El slug '{new_slug}' ya está en uso por otro producto de tu empresa.",
                    409,
                )
            update_dict["slug"] = new_slug

        if (
            "barcode" in update_dict
            and update_dict["barcode"] is not None
            and update_dict["barcode"] != product.barcode
        ):
            existing_barcode = await repository.find_one(
                {
                    "barcode": update_dict["barcode"],
                    "_id": {"$ne": product.id},
                    "is_deleted": False,
                }
            )
            if existing_barcode:
                raise AppException(
                    f"El código de barras '{update_dict['barcode']}' ya está registrado en tu empresa.",
                    409,
                )

        if (
            "sku" in update_dict
            and update_dict["sku"] is not None
            and update_dict["sku"] != product.sku
        ):
            existing_sku = await repository.find_one(
                {
                    "sku": update_dict["sku"],
                    "_id": {"$ne": product.id},
                    "is_deleted": False,
                }
            )
            if existing_sku:
                raise AppException(
                    f"El SKU '{update_dict['sku']}' ya está registrado en tu empresa.",
                    409,
                )

        if (
            "category_id" in update_dict
            and update_dict["category_id"] is not None
            and update_dict["category_id"] != product.category_id
        ):
            category = await ProductService._category_repository(repository).get(
                update_dict["category_id"]
            )
            if not category or category.is_deleted:
                raise AppException(
                    "La categoría seleccionada no existe o no pertenece a tu empresa.",
                    404,
                )

        if "attributes" in update_dict:
            attributes_raw = update_dict.pop("attributes")
            if attributes_raw is not None:
                product.attributes = [
                    ProductAttribute(
                        key=attribute["key"],
                        value=attribute["value"],
                        label=attribute["label"],
                    )
                    for attribute in attributes_raw
                ]

        for key, value in update_dict.items():
            setattr(product, key, value)

        product.updated_by = actor_id
        return await repository.save(product)

    @staticmethod
    async def delete_product(
        repository: TenantRepository[Product],
        product_id: PydanticObjectId,
        actor: User,
        hard_delete: bool = False,
    ) -> None:
        """Elimina un producto de forma lógica o permanente."""
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException(
                "Solo un SUPERADMIN puede realizar un borrado permanente.",
                403,
            )

        product = await ProductService.get_product(repository, product_id)

        if hard_delete:
            await repository.delete(product)
            return

        now = datetime.now(timezone.utc)
        product.is_deleted = True
        product.deleted_at = now
        product.deleted_by = actor.id
        product.updated_by = actor.id
        await repository.save(product)

    @staticmethod
    async def upload_image(
        repository: TenantRepository[Product],
        product_id: PydanticObjectId,
        file: UploadFile,
        actor_id: PydanticObjectId,
    ) -> Product:
        """Sube una imagen y la agrega al producto del tenant."""
        product = await ProductService.get_product(repository, product_id)

        image_url = await CloudinaryService.upload_image(file, folder="products")
        product.images.append(image_url)
        product.updated_by = actor_id
        return await repository.save(product)

    @staticmethod
    async def delete_image(
        repository: TenantRepository[Product],
        product_id: PydanticObjectId,
        image_url: str,
        actor_id: PydanticObjectId,
    ) -> Product:
        """Elimina una imagen del producto y de Cloudinary."""
        product = await ProductService.get_product(repository, product_id)

        if image_url not in product.images:
            raise AppException("La imagen especificada no existe en este producto.", 404)

        product.images.remove(image_url)
        product.updated_by = actor_id
        saved_product = await repository.save(product)

        await CloudinaryService.delete_image(image_url)
        return saved_product
