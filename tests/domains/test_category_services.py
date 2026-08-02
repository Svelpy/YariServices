"""
Tests de integración para CategoryService.
Tipo: Integration (usa BD de prueba real con Beanie).
"""
import pytest
from unittest.mock import AsyncMock, patch
from beanie import PydanticObjectId

from app.domains.category.models import Category
from app.domains.category.schemas import CategoryCreate, CategoryUpdate
from app.domains.category.services import CategoryService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(email: str, role: Role = Role.PROPIETARIO) -> User:
    u = User(email=email, role=role, status=UserStatus.ACTIVE)
    await u.save()
    return u


async def _cat(name: str, bid: PydanticObjectId, actor_id: PydanticObjectId, **kwargs) -> Category:
    return await CategoryService.create_category(
        category_data=CategoryCreate(name=name, **kwargs),
        actor_id=actor_id,
        business_id=bid,
    )


# ---------------------------------------------------------------------------
# create_category
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_category_exitosa():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Electrónica", bid, actor_id, description="Gadgets y más")

    assert cat.name == "Electrónica"
    assert cat.slug == "electronica"
    assert cat.path == "electronica"
    assert cat.level == 0
    assert cat.business_id == bid
    assert cat.created_by == actor_id


@pytest.mark.asyncio
async def test_create_category_con_padre_calcula_level_y_path():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Ropa", bid, actor_id)
    child = await _cat("Camisas", bid, actor_id, parent_id=parent.id)

    assert child.level == 1
    assert child.path == "ropa/camisas"
    assert child.parent_id == parent.id


@pytest.mark.asyncio
async def test_create_category_slug_duplicado_misma_empresa_lanza_409():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Electrónica", bid, actor_id)

    with pytest.raises(AppException) as exc:
        await _cat("Electrónica", bid, actor_id)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_category_slug_duplicado_otra_empresa_exitoso():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Electrónica", bid_a, actor_id)

    # Misma nombre en otra empresa NO debe fallar
    cat_b = await _cat("Electrónica", bid_b, actor_id)
    assert cat_b.slug == "electronica"


@pytest.mark.asyncio
async def test_create_category_padre_otra_empresa_lanza_404():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    padre = await _cat("Tecnología", bid_a, actor_id)

    with pytest.raises(AppException) as exc:
        await _cat("Subcategoria", bid_b, actor_id, parent_id=padre.id)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_category
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_category_exitoso():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Calzado", bid, actor_id)

    found = await CategoryService.get_category(cat.id, business_id=bid)
    assert found.id == cat.id


@pytest.mark.asyncio
async def test_get_category_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await CategoryService.get_category(PydanticObjectId())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_category_empresa_incorrecta_lanza_403():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Muebles", bid_a, actor_id)

    with pytest.raises(AppException) as exc:
        await CategoryService.get_category(cat.id, business_id=bid_b)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# list_categories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_retorna_correctamente():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Cat A", bid, actor_id)
    await _cat("Cat B", bid, actor_id)

    result = await CategoryService.list_categories(business_id=bid, page=1, per_page=10)
    assert result["total"] == 2
    assert len(result["data"]) == 2


@pytest.mark.asyncio
async def test_list_categories_filtra_por_texto():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Tecnología", bid, actor_id)
    await _cat("Alimentos", bid, actor_id)

    result = await CategoryService.list_categories(business_id=bid, q="Tecnología")
    assert result["total"] == 1
    assert result["data"][0].name == "Tecnología"


@pytest.mark.asyncio
async def test_list_categories_aislamiento_por_empresa():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _cat("Solo de A", bid_a, actor_id)

    result = await CategoryService.list_categories(business_id=bid_b)
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# get_categories_tree
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_categories_tree_estructura():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    parent = await _cat("Ropa", bid, actor_id)
    await _cat("Camisas", bid, actor_id, parent_id=parent.id)
    await _cat("Pantalones", bid, actor_id, parent_id=parent.id)

    tree = await CategoryService.get_categories_tree(business_id=bid)
    assert tree["total"] == 1
    assert tree["data"][0]["data"].name == "Ropa"
    assert len(tree["data"][0]["children"]) == 2


@pytest.mark.asyncio
async def test_get_categories_tree_vacio():
    bid = PydanticObjectId()
    tree = await CategoryService.get_categories_tree(business_id=bid)
    assert tree["total"] == 0
    assert tree["data"] == []


# ---------------------------------------------------------------------------
# update_category
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_category_nombre_recalcula_slug():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Nombre Viejo", bid, actor_id)

    updated = await CategoryService.update_category(
        category_id=cat.id,
        update_data=CategoryUpdate(name="Nombre Nuevo"),
        actor_id=actor_id,
        business_id=bid,
    )
    assert updated.name == "Nombre Nuevo"
    assert updated.slug == "nombre-nuevo"


@pytest.mark.asyncio
async def test_update_category_con_padre_recalcula_path():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    padre = await _cat("Tecnología", bid, actor_id)
    cat = await _cat("Subcategoria", bid, actor_id)

    updated = await CategoryService.update_category(
        category_id=cat.id,
        update_data=CategoryUpdate(parent_id=padre.id),
        actor_id=actor_id,
        business_id=bid,
    )
    assert updated.path == "tecnologia/subcategoria"
    assert updated.level == 1


@pytest.mark.asyncio
async def test_update_category_empresa_incorrecta_lanza_403():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Muebles", bid_a, actor_id)

    with pytest.raises(AppException) as exc:
        await CategoryService.update_category(
            category_id=cat.id,
            update_data=CategoryUpdate(name="Intentando"),
            actor_id=actor_id,
            business_id=bid_b,
        )
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# delete_category
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_category_soft_delete_exitoso():
    bid = PydanticObjectId()
    actor = User(email="del_cat@example.com", role=Role.PROPIETARIO, status=UserStatus.ACTIVE)
    await actor.save()
    cat = await _cat("A Eliminar", bid, actor.id)

    await CategoryService.delete_category(category_id=cat.id, actor=actor, business_id=bid)

    with pytest.raises(AppException) as exc:
        await CategoryService.get_category(cat.id, business_id=bid)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_elimina_descendientes_en_cascada():
    bid = PydanticObjectId()
    actor = User(email="del_cascade@example.com", role=Role.PROPIETARIO, status=UserStatus.ACTIVE)
    await actor.save()

    parent = await _cat("Parent", bid, actor.id)
    child = await _cat("Child", bid, actor.id, parent_id=parent.id)

    await CategoryService.delete_category(category_id=parent.id, actor=actor, business_id=bid)

    # El hijo también debe quedar eliminado
    with pytest.raises(AppException):
        await CategoryService.get_category(child.id, business_id=bid)


@pytest.mark.asyncio
async def test_delete_category_hard_delete_requiere_superadmin():
    bid = PydanticObjectId()
    gerente = User(email="gerente_del@example.com", role=Role.GERENTE, status=UserStatus.ACTIVE)
    await gerente.save()
    cat = await _cat("Protegida Hard", bid, gerente.id)

    with pytest.raises(AppException) as exc:
        await CategoryService.delete_category(
            category_id=cat.id, actor=gerente, business_id=bid, hard_delete=True
        )
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# update_banner (con Cloudinary mockeado)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_category_categoria_como_su_propio_padre_lanza_400():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Auto Padre", bid, actor_id)

    with pytest.raises(AppException) as exc:
        await CategoryService.update_category(
            category_id=cat.id,
            update_data=CategoryUpdate(parent_id=cat.id),
            actor_id=actor_id,
            business_id=bid,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_category_descendiente_como_padre_lanza_400():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    padre = await _cat("Abuelo", bid, actor_id)
    hijo = await _cat("Padre", bid, actor_id, parent_id=padre.id)

    with pytest.raises(AppException) as exc:
        await CategoryService.update_category(
            category_id=padre.id,
            update_data=CategoryUpdate(parent_id=hijo.id),
            actor_id=actor_id,
            business_id=bid,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_category_cambiar_padre_a_none():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    padre = await _cat("Raíz Inicial", bid, actor_id)
    hijo = await _cat("Hijo A Mover", bid, actor_id, parent_id=padre.id)

    updated = await CategoryService.update_category(
        category_id=hijo.id,
        update_data=CategoryUpdate(parent_id=None),
        actor_id=actor_id,
        business_id=bid,
    )
    assert updated.level == 0
    assert updated.path == "hijo-a-mover"


@pytest.mark.asyncio
async def test_update_banner_elimina_banner_anterior():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat = await _cat("Con Banner Viejo", bid, actor_id, banner_url="https://cloudinary.com/old_banner.jpg")

    mock_file = AsyncMock()
    with patch(
        "app.domains.category.services.CloudinaryService.upload_image",
        new_callable=AsyncMock,
        return_value="https://cloudinary.com/new_banner.jpg"
    ):
        with patch(
            "app.domains.category.services.CloudinaryService.delete_image",
            new_callable=AsyncMock,
            return_value=True
        ) as mock_delete:
            updated = await CategoryService.update_banner(
                category_id=cat.id,
                file=mock_file,
                actor_id=actor_id,
                business_id=bid,
            )

    assert updated.banner_url == "https://cloudinary.com/new_banner.jpg"
    mock_delete.assert_called_once_with("https://cloudinary.com/old_banner.jpg")


def test_category_model_repr_and_str():
    cat = Category(name="Tecnología", slug="tecnologia", path="tecnologia", level=0, business_id=PydanticObjectId())
    assert repr(cat) == "<Category tecnologia (Lvl: 0)>"
    assert str(cat) == "Tecnología"

