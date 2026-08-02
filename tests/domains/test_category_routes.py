"""
Tests de integración para las rutas del dominio category.
Tipo: Integration (usa BD de prueba + decode_access_token mockeado).
"""
import pytest
from unittest.mock import patch, AsyncMock
from beanie import PydanticObjectId

from app.domains.category.models import Category
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(email: str, role: Role, business_id: PydanticObjectId = None) -> User:
    u = User(email=email, role=role, status=UserStatus.ACTIVE, business_id=business_id)
    await u.save()
    return u


async def _make_category(bid: PydanticObjectId, name: str, actor_id: PydanticObjectId) -> Category:
    from app.domains.category.schemas import CategoryCreate
    from app.domains.category.services import CategoryService
    return await CategoryService.create_category(
        category_data=CategoryCreate(name=name),
        actor_id=actor_id,
        business_id=bid,
    )


def _headers():
    return {"Authorization": "Bearer fake_token"}


# ---------------------------------------------------------------------------
# GET /categories (listar)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("cat_list@example.com", Role.PROPIETARIO, business_id=bid)
    await _make_category(bid, "Electrónica", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get(f"/api/v1/categories?business_id={bid}", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_categories_denegado_sin_permiso(async_client):
    user = await _make_user("cat_vend@example.com", Role.VENDEDOR)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get("/api/v1/categories", headers=_headers())

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /categories/tree
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_categories_tree_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("cat_tree@example.com", Role.PROPIETARIO, business_id=bid)
    parent = await _make_category(bid, "Ropa Tree", user.id)
    await _make_category(bid, "Camisas Tree", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get("/api/v1/categories/tree", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1


# ---------------------------------------------------------------------------
# GET /categories/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_category_por_id_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("cat_get@example.com", Role.PROPIETARIO, business_id=bid)
    cat = await _make_category(bid, "Alimentos Get", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get(f"/api/v1/categories/{cat.id}", headers=_headers())

    assert resp.status_code == 200
    assert resp.json()["name"] == "Alimentos Get"


@pytest.mark.asyncio
async def test_get_category_no_existente_retorna_404(async_client):
    bid = PydanticObjectId()
    user = await _make_user("cat_404@example.com", Role.PROPIETARIO, business_id=bid)
    fake_id = PydanticObjectId()

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get(f"/api/v1/categories/{fake_id}", headers=_headers())

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /categories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_category_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("cat_create@example.com", Role.PROPIETARIO, business_id=bid)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.post(
            "/api/v1/categories",
            json={"name": "Nueva Categoría"},
            headers=_headers(),
        )

    assert resp.status_code == 201
    assert resp.json()["name"] == "Nueva Categoría"


@pytest.mark.asyncio
async def test_create_category_denegado_para_almacen(async_client):
    user = await _make_user("cat_alm@example.com", Role.ALMACEN)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.post(
            "/api/v1/categories",
            json={"name": "Intento"},
            headers=_headers(),
        )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /categories/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_category_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("cat_upd@example.com", Role.PROPIETARIO, business_id=bid)
    cat = await _make_category(bid, "Viejo Nombre Cat", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.patch(
            f"/api/v1/categories/{cat.id}",
            json={"name": "Nuevo Nombre Cat"},
            headers=_headers(),
        )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Nuevo Nombre Cat"


# ---------------------------------------------------------------------------
# POST /categories/{id}/banner
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_banner_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("banner_owner@example.com", Role.PROPIETARIO, business_id=bid)
    cat = await _make_category(bid, "Con Banner Ruta", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        with patch(
            "app.domains.category.services.CloudinaryService.upload_image",
            new_callable=AsyncMock,
            return_value="https://cloudinary.com/test.jpg",
        ):
            resp = await async_client.post(
                f"/api/v1/categories/{cat.id}/banner",
                files={"file": ("test.jpg", b"fake_image_bytes", "image/jpeg")},
                headers=_headers(),
            )

    assert resp.status_code == 200
    assert resp.json()["banner_url"] == "https://cloudinary.com/test.jpg"


# ---------------------------------------------------------------------------
# DELETE /categories/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_category_exitoso(async_client):
    bid = PydanticObjectId()
    superadmin = await _make_user("cat_del_super@example.com", Role.SUPERADMIN)
    propietario = await _make_user("cat_del_owner@example.com", Role.PROPIETARIO, business_id=bid)
    cat = await _make_category(bid, "Categoria A Borrar Ruta", propietario.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(superadmin.id)}):
        resp = await async_client.delete(
            f"/api/v1/categories/{cat.id}?business_id={bid}",
            headers=_headers(),
        )

    assert resp.status_code == 204
