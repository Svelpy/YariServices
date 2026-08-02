import math
import re
from datetime import datetime, timezone
from typing import Any, Dict

from beanie import PydanticObjectId
from beanie.operators import Or, RegEx
from fastapi import UploadFile

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
    async def create_product(
        product_data: ProductCreate,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId,
    ) -> Product:
        """
        Crea un nuevo producto en el catálogo de una empresa.
        Genera el slug automáticamente y valida la unicidad de slug, barcode y SKU por empresa.
        """
        # Generar slug a partir del nombre
        slug = generate_slug(product_data.name)
        if not slug:
            raise AppException("El nombre del producto no genera un slug válido.", 400)

        # Verificar unicidad del slug en la misma empresa
        existing_slug = await Product.find_one(
            Product.business_id == business_id,
            Product.slug == slug,
            Product.is_deleted == False,
        )
        if existing_slug:
            raise AppException(f"El slug '{slug}' ya está registrado en otro producto activo de tu empresa.", 409)

        # Verificar unicidad del código de barras (si se proporciona)
        if product_data.barcode:
            existing_barcode = await Product.find_one(
                Product.business_id == business_id,
                Product.barcode == product_data.barcode,
                Product.is_deleted == False,
            )
            if existing_barcode:
                raise AppException(f"El código de barras '{product_data.barcode}' ya está registrado en tu empresa.", 409)

        # Verificar unicidad del SKU (si se proporciona)
        if product_data.sku:
            existing_sku = await Product.find_one(
                Product.business_id == business_id,
                Product.sku == product_data.sku,
                Product.is_deleted == False,
            )
            if existing_sku:
                raise AppException(f"El SKU '{product_data.sku}' ya está registrado en tu empresa.", 409)

        # Validar que la categoría exista y pertenezca a la misma empresa (si se indica category_id)
        if product_data.category_id:
            category = await Category.get(product_data.category_id)
            if not category or category.is_deleted or category.business_id != business_id:
                raise AppException("La categoría seleccionada no existe o no pertenece a tu empresa.", 404)

        # Mapear atributos polimórficos
        attribute_models = [
            ProductAttribute(key=attr.key, value=attr.value, label=attr.label)
            for attr in product_data.attributes
        ]

        product = Product(
            business_id=business_id,
            name=product_data.name,
            slug=slug,
            barcode=product_data.barcode,
            sku=product_data.sku,
            presentation=product_data.presentation,
            category_id=product_data.category_id,
            brand=product_data.brand,
            description=product_data.description,
            cost=product_data.cost,
            sale_price=product_data.sale_price,
            wholesale_price=product_data.wholesale_price,
            min_stock=product_data.min_stock,
            attributes=attribute_models,
            images=product_data.images,
            is_active=product_data.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )

        await product.save()
        return product

    @staticmethod
    async def get_product(
        product_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Product:
        """
        Obtiene un producto por su ID, asegurando el aislamiento por empresa si se especifica business_id.
        """
        product = await Product.get(product_id)
        if not product or product.is_deleted:
            raise AppException("Producto no encontrado.", 404)

        if business_id is not None and product.business_id != business_id:
            raise AppException("No tienes permisos para acceder a este producto.", 403)

        return product

    @staticmethod
    async def get_product_by_slug(slug: str, business_id: PydanticObjectId) -> Product:
        """
        Obtiene un producto activo por su slug dentro de una empresa.
        """
        product = await Product.find_one(
            Product.business_id == business_id,
            Product.slug == slug,
            Product.is_deleted == False,
        )
        if not product:
            raise AppException("Producto no encontrado.", 404)
        return product

    @staticmethod
    async def list_products(
        business_id: PydanticObjectId,
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        category_id: PydanticObjectId | None = None,
        is_active: bool | None = None,
    ) -> Dict[str, Any]:
        """
        Lista productos de una empresa con soporte para filtrado por categoría, estado, búsqueda por texto y paginación.
        """
        query = Product.find(
            Product.business_id == business_id,
            Product.is_deleted == False,
        )

        if category_id is not None:
            query = query.find(Product.category_id == category_id)

        if is_active is not None:
            query = query.find(Product.is_active == is_active)

        if q:
            safe_q = re.escape(q)
            query = query.find(Or(
                RegEx(Product.name, safe_q, "i"),
                RegEx(Product.slug, safe_q, "i"),
                RegEx(Product.barcode, safe_q, "i"),
                RegEx(Product.sku, safe_q, "i"),
                RegEx(Product.brand, safe_q, "i"),
                RegEx(Product.description, safe_q, "i"),
            ))

        total_count = await query.count()
        skip = (page - 1) * per_page
        products = await query.sort(+Product.name).skip(skip).limit(per_page).to_list()
        total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "data": products,
        }

    @staticmethod
    async def update_product(
        product_id: PydanticObjectId,
        update_data: ProductUpdate,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Product:
        """
        Actualiza los datos de un producto (precios, stock, categoría, atributos dinámicos).
        Recalcula el slug si el nombre cambia.
        """
        product = await ProductService.get_product(product_id, business_id=business_id)
        update_dict = update_data.model_dump(exclude_unset=True)

        # Validación de cambio de nombre / slug
        if ("name" in update_dict) and (update_dict["name"] != product.name):
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException("El nombre proporcionado no genera un slug válido.", 400)

            existing_slug = await Product.find_one(
                Product.business_id == product.business_id,
                Product.slug == new_slug,
                Product.id != product.id,
                Product.is_deleted == False,
            )
            if existing_slug:
                raise AppException(f"El slug '{new_slug}' ya está en uso por otro producto de tu empresa.", 409)
            update_dict["slug"] = new_slug

        # Validación de código de barras
        if ("barcode" in update_dict) and (update_dict["barcode"] is not None) and (update_dict["barcode"] != product.barcode):
            existing_barcode = await Product.find_one(
                Product.business_id == product.business_id,
                Product.barcode == update_dict["barcode"],
                Product.id != product.id,
                Product.is_deleted == False,
            )
            if existing_barcode:
                raise AppException(f"El código de barras '{update_dict['barcode']}' ya está registrado en tu empresa.", 409)

        # Validación de SKU
        if ("sku" in update_dict) and (update_dict["sku"] is not None) and (update_dict["sku"] != product.sku):
            existing_sku = await Product.find_one(
                Product.business_id == product.business_id,
                Product.sku == update_dict["sku"],
                Product.id != product.id,
                Product.is_deleted == False,
            )
            if existing_sku:
                raise AppException(f"El SKU '{update_dict['sku']}' ya está registrado en tu empresa.", 409)

        # Validación de categoría
        if ("category_id" in update_dict) and (update_dict["category_id"] is not None) and (update_dict["category_id"] != product.category_id):
            category = await Category.get(update_dict["category_id"])
            if not category or category.is_deleted or category.business_id != product.business_id:
                raise AppException("La categoría seleccionada no existe o no pertenece a tu empresa.", 404)

        # Mapear atributos polimórficos si se actualizaron
        if "attributes" in update_dict:
            attributes_raw = update_dict.pop("attributes")
            if attributes_raw is not None:
                product.attributes = [
                    ProductAttribute(key=attr["key"], value=attr["value"], label=attr["label"])
                    for attr in attributes_raw
                ]

        for key, value in update_dict.items():
            setattr(product, key, value)

        product.updated_by = actor_id
        await product.save()
        return product

    @staticmethod
    async def delete_product(
        product_id: PydanticObjectId,
        actor: User,
        business_id: PydanticObjectId | None = None,
        hard_delete: bool = False,
    ) -> None:
        """
        Elimina un producto (soft delete por defecto, hard delete para SUPERADMIN).
        """
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException("Solo un SUPERADMIN puede realizar un borrado permanente.", 403)

        product = await ProductService.get_product(product_id, business_id=business_id)

        if hard_delete:
            await product.delete()
        else:
            now = datetime.now(timezone.utc)
            product.is_deleted = True
            product.deleted_at = now
            product.deleted_by = actor.id
            product.updated_by = actor.id
            await product.save()

    @staticmethod
    async def upload_image(
        product_id: PydanticObjectId,
        file: UploadFile,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Product:
        """
        Sube una imagen del producto a Cloudinary y la añade a la lista de imágenes del producto.
        """
        product = await ProductService.get_product(product_id, business_id=business_id)

        image_url = await CloudinaryService.upload_image(file, folder="products")
        product.images.append(image_url)
        product.updated_by = actor_id
        await product.save()

        return product

    @staticmethod
    async def delete_image(
        product_id: PydanticObjectId,
        image_url: str,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Product:
        """
        Elimina una imagen específica del producto (de la lista y de Cloudinary).
        """
        product = await ProductService.get_product(product_id, business_id=business_id)

        if image_url not in product.images:
            raise AppException("La imagen especificada no existe en este producto.", 404)

        product.images.remove(image_url)
        product.updated_by = actor_id
        await product.save()

        await CloudinaryService.delete_image(image_url)
        return product
