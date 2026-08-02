import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from beanie import PydanticObjectId
from beanie.operators import Or, RegEx
from fastapi import UploadFile

from app.domains.category.models import Category
from app.domains.category.schemas import CategoryCreate, CategoryUpdate
from app.domains.users.models import User
from app.integrations.cloudinary import CloudinaryService
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug


class CategoryService:

    @staticmethod
    async def create_category(
        category_data: CategoryCreate,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId,
    ) -> Category:
        """
        Crea una nueva categoría perteneciente a una empresa específica.
        Genera el slug y path de forma automática y valida la jerarquía.
        """
        # Generar slug
        slug = generate_slug(category_data.name)
        if not slug:
            raise AppException("El slug no puede ser vacío y debe ser válido.", 400)

        # Verificar unicidad de slug dentro de la misma empresa
        existing_slug = await Category.find_one(
            Category.business_id == business_id,
            Category.slug == slug,
            Category.is_deleted == False,
        )
        if existing_slug:
            raise AppException(f"El slug '{slug}' ya está registrado en otra categoría activa de tu empresa.", 409)

        #Inicializamos level y path
        level = 0
        path = slug

        # Si tiene padre, validamos que pertenezca a la misma empresa
        if category_data.parent_id:
            parent = await Category.get(category_data.parent_id)
            if not parent or parent.is_deleted or parent.business_id != business_id:
                raise AppException("La categoría padre especificada no existe o fue eliminada.", 404)

            level = parent.level + 1
            path = f"{parent.path}/{slug}"


        # Crear y guardar la categoría
        category = Category(
            business_id=business_id,
            name=category_data.name,
            slug=slug,
            path=path,
            description=category_data.description,
            parent_id=category_data.parent_id,
            level=level,
            display_order=category_data.display_order,
            banner_url=category_data.banner_url,
            is_active=category_data.is_active,
            meta_title=category_data.meta_title,
            meta_description=category_data.meta_description,
            created_by=actor_id,
            updated_by=actor_id,
        )

        await category.save()
        return category

    @staticmethod
    async def get_categories_tree(business_id: PydanticObjectId) -> Dict[str, Any]:
        """
        Construye y retorna el árbol completo de categorías activas ordenadas de una empresa.
        """
        # Traer todas las categorías activas
        categories = await Category.find(
            Category.business_id == business_id,
            Category.is_deleted == False,
        ).sort(
            +Category.level,
            +Category.display_order,
            +Category.name,
        ).to_list()

        nodes: Dict[PydanticObjectId, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []

        # Crear mapeo de nodos
        for cat in categories:
            nodes[cat.id] = {
                "data": cat,
                "children": [],
            }

        # Construir relaciones jerárquicas
        for cat in categories:
            node = nodes[cat.id]
            if cat.parent_id is None:
                roots.append(node)
            else:
                if cat.parent_id in nodes:
                    nodes[cat.parent_id]["children"].append(node)
                else:
                    # Si el padre no está (por ejemplo, eliminado o huérfano), se coloca en la raíz
                    roots.append(node)

        return {
            "total": len(roots),
            "data": roots,
        }

    @staticmethod
    async def get_category(
        category_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Category:
        """
        Obtiene una categoría activa por su ID, asegurando el aislamiento por empresa si se indica business_id.
        """
        category = await Category.get(category_id)
        if not category or category.is_deleted:
            raise AppException("Categoría no existente.", 404)

        if business_id is not None and category.business_id != business_id:
            raise AppException("No tienes permiso para acceder a esta categoría.", 403)

        return category

    @staticmethod
    async def list_categories(
        business_id: PydanticObjectId,
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        parent_id: PydanticObjectId | None = None,
    ) -> Dict[str, Any]:
        """
        Lista categorías de una empresa con soporte para búsqueda y paginación.
        """
        query = Category.find(
            Category.business_id == business_id,
            Category.is_deleted == False,
            Category.parent_id == parent_id,
        )
        # Búsqueda por query
        if q:
            safe_q = re.escape(q)
            query = query.find(Or(
                RegEx(Category.name, safe_q, "i"),
                RegEx(Category.slug, safe_q, "i"),
                RegEx(Category.description, safe_q, "i"),
            ))

        total_count = await query.count()
        skip = (page - 1) * per_page

        # Ordenar por orden de visualización y nombre
        categories = await query.sort(
            +Category.display_order,
            +Category.name,
        ).skip(skip).limit(per_page).to_list()

        total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "data": categories,
        }

    @staticmethod
    async def update_category(
        category_id: PydanticObjectId,
        update_data: CategoryUpdate,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Category:
        """
        Actualiza los datos de una categoría. Si cambia el slug o el parent_id,
        recalcula el path y level de la categoría y de toda su descendencia dentro de la empresa.
        """
        category = await CategoryService.get_category(category_id, business_id=business_id)
        update_dict = update_data.model_dump(exclude_unset=True)

        # Si se incluye "name" en la actualización y es diferente, generamos el slug automáticamente
        if ("name" in update_dict) and (update_dict["name"] != category.name):
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException("El nombre proporcionado no genera un slug válido.", 400)

            existing_slug = await Category.find_one(
                Category.business_id == category.business_id,
                Category.slug == new_slug,
                Category.id != category.id,
                Category.is_deleted == False,
            )
            if existing_slug:
                raise AppException(f"El slug '{new_slug}' ya está en uso por otra categoría de tu empresa.", 409)
            update_dict["slug"] = new_slug

        slug_changed = ("slug" in update_dict) and (update_dict["slug"] != category.slug)
        parent_changed = ("parent_id" in update_dict) and (update_dict["parent_id"] != category.parent_id)

        if parent_changed or slug_changed:
            new_parent_id = update_dict.get("parent_id", category.parent_id)
            new_slug = update_dict.get("slug", category.slug)

            if parent_changed:
                if new_parent_id is not None:
                    if new_parent_id == category.id:
                        raise AppException("Una categoría no puede ser su propio padre.", 400)

                    new_parent = await Category.get(new_parent_id)
                    if not new_parent or new_parent.is_deleted or new_parent.business_id != category.business_id:
                        raise AppException("La categoría padre seleccionada no existe o pertenece a otra empresa.", 404)

                    if new_parent.path == category.path or new_parent.path.startswith(f"{category.path}/"):
                        raise AppException("Una categoría no puede tener como padre a uno de sus propios descendientes.", 400)

                    new_level = new_parent.level + 1
                    new_path = f"{new_parent.path}/{new_slug}"
                else:
                    new_level = 0
                    new_path = new_slug
            else:
                # Solo cambió el slug, mantener el padre actual
                if category.parent_id:
                    parent = await Category.get(category.parent_id)
                    new_level = parent.level + 1
                    new_path = f"{parent.path}/{new_slug}"
                else:
                    new_level = 0
                    new_path = new_slug

            old_path = category.path
            old_level = category.level

            update_dict["path"] = new_path
            update_dict["level"] = new_level

            # Actualizar descendientes en cascada
            descendants = await Category.find(
                Category.business_id == category.business_id,
                RegEx(Category.path, f"^{re.escape(old_path)}/"),
                Category.is_deleted == False,
            ).to_list()

            for desc in descendants:
                # Reemplazar el prefijo viejo de la ruta por el nuevo
                desc.path = new_path + desc.path[len(old_path):]
                desc.level = desc.level + (new_level - old_level)
                desc.updated_by = actor_id
                await desc.save()

        # Aplicar el resto de actualizaciones a los campos del documento
        for key, value in update_dict.items():
            setattr(category, key, value)

        category.updated_by = actor_id
        await category.save()
        return category

    @staticmethod
    async def update_banner(
        category_id: PydanticObjectId,
        file: UploadFile,
        actor_id: PydanticObjectId,
        business_id: PydanticObjectId | None = None,
    ) -> Category:
        """
        Sube la imagen del banner de la categoría a Cloudinary y elimina la anterior si existía.
        """
        category = await CategoryService.get_category(category_id, business_id=business_id)

        new_banner_url = await CloudinaryService.upload_image(file, folder="categories")
        old_banner_url = category.banner_url

        category.banner_url = new_banner_url
        category.updated_by = actor_id
        await category.save()

        if old_banner_url is not None:
            await CloudinaryService.delete_image(old_banner_url)
        return category

    @staticmethod
    async def delete_category(
        category_id: PydanticObjectId,
        actor: User,
        business_id: PydanticObjectId | None = None,
        hard_delete: bool = False,
    ) -> None:
        """
        Realiza un borrado lógico (soft delete) de una categoría y de toda su descendencia dentro de la empresa.
        """
        if hard_delete and actor.role != Role.SUPERADMIN:
            raise AppException("Solo un SUPERADMIN puede realizar un borrado permanente.", 403)

        category = await CategoryService.get_category(category_id, business_id=business_id)

        descendants = await Category.find(
            Category.business_id == category.business_id,
            RegEx(Category.path, f"^{re.escape(category.path)}/"),
            Category.is_deleted == False,
        ).to_list()

        if hard_delete:
            await category.delete()
            for desc in descendants:
                await desc.delete()
        else:
            now = datetime.now(timezone.utc)
            category.is_deleted = True
            category.deleted_at = now
            category.deleted_by = actor.id
            await category.save()
            for desc in descendants:
                desc.is_deleted = True
                desc.deleted_at = now
                desc.deleted_by = actor.id
                await desc.save()
