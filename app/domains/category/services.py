import math
import re
from datetime import datetime, timezone
from typing import Any

from beanie import PydanticObjectId
from fastapi import UploadFile

from app.core.repositories import TenantRepository
from app.integrations.cloudinary import CloudinaryService
from app.domains.auth import CurrentUser
from app.domains.category.models import Category
from app.domains.category.schemas import CategoryCreate, CategoryUpdate
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException
from app.shared.services.slug import generate_slug


class CategoryService:

    @staticmethod
    async def create_category(
        repository: TenantRepository[Category],
        category_data: CategoryCreate,
        actor_id: PydanticObjectId,
    ) -> Category:
        slug = generate_slug(category_data.name)
        if not slug:
            raise AppException("El slug no puede estar vacío y debe ser válido.", 400)

        existing_slug = await repository.find_one({"slug": slug,"is_deleted": False,})

        if existing_slug:
            raise AppException(f"El slug '{slug}' ya está registrado en otra categoría activa de tu empresa.",409,)

        level = 0
        path = slug

        if category_data.parent_id:
            parent = await repository.get(category_data.parent_id)
            if not parent or parent.is_deleted:
                raise AppException("La categoría padre especificada no existe o fue eliminada.",404,)

            level = parent.level + 1
            path = f"{parent.path}/{slug}"

        category = Category(
            business_id=repository.business_id,
            name=category_data.name,
            slug=slug,
            path=path,
            description=category_data.description,
            parent_id=category_data.parent_id,
            level=level,
            display_order=category_data.display_order,
            is_active=category_data.is_active,
            meta_title=category_data.meta_title,
            meta_description=category_data.meta_description,
            created_by=actor_id,
            updated_by=actor_id,
        )

        return await repository.create(category)

    @staticmethod
    async def get_categories_tree(
        repository: TenantRepository[Category],
    ) -> dict[str, Any]:
        categories = await repository.list(
            {
                "is_active": True,
                "is_deleted": False,
            },
            sort=(
                +Category.level,
                +Category.display_order,
                +Category.name,
            ),
        )

        nodes: dict[PydanticObjectId, dict[str, Any]] = {}
        roots: list[dict[str, Any]] = []

        for category in categories:
            nodes[category.id] = {
                "data": category,
                "children": [],
            }

        for category in categories:
            node = nodes[category.id]
            if category.parent_id is None:
                roots.append(node)
            elif category.parent_id in nodes:
                nodes[category.parent_id]["children"].append(node)
            else:
                roots.append(node)

        return {
            "total": len(roots),
            "data": roots,
        }

    @staticmethod
    async def get_category(
        repository: TenantRepository[Category],
        category_id: PydanticObjectId,
    ) -> Category:
        category = await repository.get(category_id)

        if not category or category.is_deleted:
            raise AppException("Categoría no existente.", 404)

        return category

    @staticmethod
    async def list_categories(
        repository: TenantRepository[Category],
        page: int = 1,
        per_page: int = 10,
        q: str | None = None,
        parent_id: PydanticObjectId | None = None,
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {
            "parent_id": parent_id,
            "is_deleted": False,
        }

        if q:
            pattern = re.escape(q)
            filters["$or"] = [
                {"name": {"$regex": pattern, "$options": "i"}},
                {"slug": {"$regex": pattern, "$options": "i"}},
                {"description": {"$regex": pattern, "$options": "i"}},
            ]

        total_count = await repository.count(filters)
        skip = (page - 1) * per_page
        categories = await repository.list(
            filters,
            skip=skip,
            limit=per_page,
            sort=(+Category.display_order, +Category.name),
        )

        return {
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total_count / per_page) if per_page > 0 else 0,
            "data": categories,
        }

    @staticmethod
    async def update_category(
        repository: TenantRepository[Category],
        category_id: PydanticObjectId,
        update_data: CategoryUpdate,
        actor_id: PydanticObjectId,
    ) -> Category:
        category = await CategoryService.get_category(repository, category_id)
        update_dict = update_data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"] != category.name:
            new_slug = generate_slug(update_dict["name"])
            if not new_slug:
                raise AppException("El nombre proporcionado no genera un slug válido.",400)

            existing_slug = await repository.find_one(
                {
                    "slug": new_slug,
                    "_id": {"$ne": category.id},
                    "is_deleted": False,
                }
            )
            if existing_slug:
                raise AppException(f"El slug '{new_slug}' ya está en uso por otra categoría de tu empresa.",409)

            update_dict["slug"] = new_slug

        slug_changed = (
            update_dict.get("slug") != category.slug
            if "slug" in update_dict
            else False
        )
        parent_changed = (
            update_dict.get("parent_id") != category.parent_id
            if "parent_id" in update_dict
            else False
        )

        if parent_changed or slug_changed:
            new_parent_id = update_dict.get("parent_id", category.parent_id)
            new_slug = update_dict.get("slug", category.slug)

            if parent_changed and new_parent_id is not None:
                if new_parent_id == category.id:
                    raise AppException("Una categoría no puede ser su propio padre.", 400)

                new_parent = await repository.get(new_parent_id)
                if not new_parent or new_parent.is_deleted:
                    raise AppException("La categoría padre seleccionada no existe o pertenece a otra empresa.",404)

                if new_parent.path == category.path or new_parent.path.startswith(f"{category.path}/"):
                    raise AppException("Una categoría no puede tener como padre a uno de sus propios descendientes.",400)

                new_level = new_parent.level + 1
                new_path = f"{new_parent.path}/{new_slug}"
            elif parent_changed:
                new_level = 0
                new_path = new_slug
            elif category.parent_id is not None:
                parent = await repository.get(category.parent_id)
                if not parent or parent.is_deleted:
                    raise AppException("La categoría padre no existe o fue eliminada.", 404)

                new_level = parent.level + 1
                new_path = f"{parent.path}/{new_slug}"
            else:
                new_level = 0
                new_path = new_slug

            old_path = category.path
            old_level = category.level
            update_dict["path"] = new_path
            update_dict["level"] = new_level

            descendants = await repository.list(
                {
                    "path": {"$regex": f"^{re.escape(old_path)}/"},
                    "is_deleted": False,
                }
            )
            for descendant in descendants:
                descendant.path = new_path + descendant.path[len(old_path):]
                descendant.level += new_level - old_level
                descendant.updated_by = actor_id
                await repository.save(descendant)

        for field, value in update_dict.items():
            setattr(category, field, value)

        category.updated_by = actor_id
        return await repository.save(category)

    @staticmethod
    async def update_banner(
        repository: TenantRepository[Category],
        category_id: PydanticObjectId,
        file: UploadFile,
        actor_id: PydanticObjectId,
    ) -> Category:
        category = await CategoryService.get_category(repository, category_id)
        new_banner_url = await CloudinaryService.upload_image(file, folder="categories")
        old_banner_url = category.banner_url

        category.banner_url = new_banner_url
        category.updated_by = actor_id
        await repository.save(category)

        if old_banner_url is not None:
            await CloudinaryService.safe_delete_image(old_banner_url)

        return category

    @staticmethod
    async def delete_category(
        repository: TenantRepository[Category],
        category_id: PydanticObjectId,
        actor: CurrentUser,
        hard_delete: bool = False,
    ) -> None:
        if hard_delete and actor.role != Role.PROPIETARIO:
            raise AppException("Solo el PROPIETARIO puede realizar un borrado permanente.",403)

        category = await CategoryService.get_category(repository, category_id)
        descendants = await repository.list(
            {
                "path": {"$regex": f"^{re.escape(category.path)}/"},
                "is_deleted": False,
            }
        )

        now = datetime.now(timezone.utc)
        for document in [category, *descendants]:
            if hard_delete:
                await repository.delete(document)
                continue

            document.is_deleted = True
            document.deleted_at = now
            document.updated_at = now
            document.deleted_by = actor.id
            document.updated_by = actor.id
            await repository.save(document)
