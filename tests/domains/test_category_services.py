"""
Tests de integracion para CategoryService.
Tipo: Integration (usa BD de prueba real con Beanie).
"""

from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId

from app.core.repositories import TenantRepository
from app.domains.category.models import Category
from app.domains.category.schemas import CategoryCreate, CategoryUpdate
from app.domains.category.services import CategoryService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException


async def _make_user(email: str, role: Role = Role.PROPIETARIO) -> User:
    user = User(email=email, role=role, status=UserStatus.ACTIVE)
    await user.save()
    return user


def _repo(business_id: PydanticObjectId) -> TenantRepository[Category]:
    return TenantRepository(Category, business_id)


async def _cat(
    name: str,
    business_id: PydanticObjectId,
    actor_id: PydanticObjectId,
    **kwargs,
) -> Category:
    return await CategoryService.create_category(
        repository=_repo(business_id),
        category_data=CategoryCreate(name=name, **kwargs),
        actor_id=actor_id,
    )


@pytest.mark.asyncio
async def test_create_category_exitosa():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()

    category = await _cat(
        "Electrónica",
        business_id,
        actor_id,
        description="Gadgets y más",
    )

    assert category.name == "Electrónica"
    assert category.slug == "electronica"
    assert category.path == "electronica"
    assert category.level == 0
    assert category.business_id == business_id
    assert category.created_by == actor_id


@pytest.mark.asyncio
async def test_create_category_con_padre_calcula_level_y_path():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Ropa", business_id, actor_id)

    child = await _cat(
        "Camisas",
        business_id,
        actor_id,
        parent_id=parent.id,
    )

    assert child.level == 1
    assert child.path == "ropa/camisas"
    assert child.parent_id == parent.id


@pytest.mark.asyncio
async def test_create_category_slug_duplicado_misma_empresa_lanza_409():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Electrónica", business_id, actor_id)

    with pytest.raises(AppException) as exc:
        await _cat("Electrónica", business_id, actor_id)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_category_slug_duplicado_otra_empresa_exitoso():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Electrónica", business_id_a, actor_id)

    category_b = await _cat("Electrónica", business_id_b, actor_id)

    assert category_b.slug == "electronica"


@pytest.mark.asyncio
async def test_create_category_padre_otra_empresa_lanza_404():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Tecnología", business_id_a, actor_id)

    with pytest.raises(AppException) as exc:
        await _cat(
            "Subcategoria",
            business_id_b,
            actor_id,
            parent_id=parent.id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_category_exitoso():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _cat("Calzado", business_id, actor_id)

    found = await CategoryService.get_category(_repo(business_id), category.id)

    assert found.id == category.id


@pytest.mark.asyncio
async def test_get_category_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await CategoryService.get_category(_repo(PydanticObjectId()), PydanticObjectId())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_category_empresa_incorrecta_lanza_404():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _cat("Muebles", business_id_a, actor_id)

    with pytest.raises(AppException) as exc:
        await CategoryService.get_category(_repo(business_id_b), category.id)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_categories_retorna_correctamente():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Cat A", business_id, actor_id)
    await _cat("Cat B", business_id, actor_id)

    result = await CategoryService.list_categories(
        _repo(business_id),
        page=1,
        per_page=10,
    )

    assert result["total"] == 2
    assert len(result["data"]) == 2


@pytest.mark.asyncio
async def test_list_categories_filtra_por_texto():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Tecnología", business_id, actor_id)
    await _cat("Alimentos", business_id, actor_id)

    result = await CategoryService.list_categories(_repo(business_id), q="Tecnología")

    assert result["total"] == 1
    assert result["data"][0].name == "Tecnología"


@pytest.mark.asyncio
async def test_list_categories_aislamiento_por_empresa():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Solo de A", business_id_a, actor_id)

    result = await CategoryService.list_categories(_repo(business_id_b))

    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_categories_tree_estructura():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Ropa", business_id, actor_id)
    await _cat("Camisas", business_id, actor_id, parent_id=parent.id)
    await _cat("Pantalones", business_id, actor_id, parent_id=parent.id)

    tree = await CategoryService.get_categories_tree(_repo(business_id))

    assert tree["total"] == 1
    assert tree["data"][0]["data"].name == "Ropa"
    assert len(tree["data"][0]["children"]) == 2


@pytest.mark.asyncio
async def test_get_categories_tree_vacio():
    tree = await CategoryService.get_categories_tree(_repo(PydanticObjectId()))

    assert tree["total"] == 0
    assert tree["data"] == []


@pytest.mark.asyncio
async def test_update_category_nombre_recalcula_slug():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _cat("Nombre Viejo", business_id, actor_id)

    updated = await CategoryService.update_category(
        repository=_repo(business_id),
        category_id=category.id,
        update_data=CategoryUpdate(name="Nombre Nuevo"),
        actor_id=actor_id,
    )

    assert updated.name == "Nombre Nuevo"
    assert updated.slug == "nombre-nuevo"


@pytest.mark.asyncio
async def test_update_category_con_padre_recalcula_path():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Tecnología", business_id, actor_id)
    category = await _cat("Subcategoria", business_id, actor_id)

    updated = await CategoryService.update_category(
        repository=_repo(business_id),
        category_id=category.id,
        update_data=CategoryUpdate(parent_id=parent.id),
        actor_id=actor_id,
    )

    assert updated.path == "tecnologia/subcategoria"
    assert updated.level == 1


@pytest.mark.asyncio
async def test_update_category_empresa_incorrecta_lanza_404():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _cat("Muebles", business_id_a, actor_id)

    with pytest.raises(AppException) as exc:
        await CategoryService.update_category(
            repository=_repo(business_id_b),
            category_id=category.id,
            update_data=CategoryUpdate(name="Intentando"),
            actor_id=actor_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_soft_delete_exitoso():
    business_id = PydanticObjectId()
    actor = await _make_user("del_cat@example.com")
    category = await _cat("A Eliminar", business_id, actor.id)

    await CategoryService.delete_category(
        repository=_repo(business_id),
        category_id=category.id,
        actor=actor,
    )

    with pytest.raises(AppException) as exc:
        await CategoryService.get_category(_repo(business_id), category.id)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_elimina_descendientes_en_cascada():
    business_id = PydanticObjectId()
    actor = await _make_user("del_cascade@example.com")
    parent = await _cat("Parent", business_id, actor.id)
    child = await _cat("Child", business_id, actor.id, parent_id=parent.id)

    await CategoryService.delete_category(
        repository=_repo(business_id),
        category_id=parent.id,
        actor=actor,
    )

    with pytest.raises(AppException):
        await CategoryService.get_category(_repo(business_id), child.id)


@pytest.mark.asyncio
async def test_delete_category_hard_delete_requiere_superadmin():
    business_id = PydanticObjectId()
    manager = await _make_user("gerente_del@example.com", Role.GERENTE)
    category = await _cat("Protegida Hard", business_id, manager.id)

    with pytest.raises(AppException) as exc:
        await CategoryService.delete_category(
            repository=_repo(business_id),
            category_id=category.id,
            actor=manager,
            hard_delete=True,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_category_categoria_como_su_propio_padre_lanza_400():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _cat("Auto Padre", business_id, actor_id)

    with pytest.raises(AppException) as exc:
        await CategoryService.update_category(
            repository=_repo(business_id),
            category_id=category.id,
            update_data=CategoryUpdate(parent_id=category.id),
            actor_id=actor_id,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_category_descendiente_como_padre_lanza_400():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Abuelo", business_id, actor_id)
    child = await _cat("Padre", business_id, actor_id, parent_id=parent.id)

    with pytest.raises(AppException) as exc:
        await CategoryService.update_category(
            repository=_repo(business_id),
            category_id=parent.id,
            update_data=CategoryUpdate(parent_id=child.id),
            actor_id=actor_id,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_category_cambiar_padre_a_none():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Raíz Inicial", business_id, actor_id)
    child = await _cat("Hijo A Mover", business_id, actor_id, parent_id=parent.id)

    updated = await CategoryService.update_category(
        repository=_repo(business_id),
        category_id=child.id,
        update_data=CategoryUpdate(parent_id=None),
        actor_id=actor_id,
    )

    assert updated.level == 0
    assert updated.path == "hijo-a-mover"


@pytest.mark.asyncio
async def test_update_banner_elimina_banner_anterior():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _cat(
        "Con Banner Viejo",
        business_id,
        actor_id,
        banner_url="https://cloudinary.com/old_banner.jpg",
    )
    mock_file = AsyncMock()

    with patch(
        "app.domains.category.services.CloudinaryService.upload_image",
        new_callable=AsyncMock,
        return_value="https://cloudinary.com/new_banner.jpg",
    ):
        with patch(
            "app.domains.category.services.CloudinaryService.delete_image",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            updated = await CategoryService.update_banner(
                repository=_repo(business_id),
                category_id=category.id,
                file=mock_file,
                actor_id=actor_id,
            )

    assert updated.banner_url == "https://cloudinary.com/new_banner.jpg"
    mock_delete.assert_called_once_with("https://cloudinary.com/old_banner.jpg")


def test_category_model_repr_and_str():
    category = Category(
        name="Tecnología",
        slug="tecnologia",
        path="tecnologia",
        level=0,
        display_order=0,
        business_id=PydanticObjectId(),
    )

    assert repr(category) == "<Category tecnologia (Lvl: 0)>"
    assert str(category) == "Tecnología"
