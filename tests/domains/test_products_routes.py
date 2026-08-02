"""
Tests de integración para las rutas del dominio products.
Tipo: Integration (usa BD de prueba + decode_access_token mockeado).
"""
import pytest
from unittest.mock import patch, AsyncMock
from beanie import PydanticObjectId

from app.domains.products.models import Product
from app.domains.products.schemas import ProductCreate
from app.domains.products.services import ProductService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(email: str, role: Role, business_id: PydanticObjectId = None) -> User:
    u = User(email=email, role=role, status=UserStatus.ACTIVE, business_id=business_id)
    await u.save()
    return u


async def _make_product(bid: PydanticObjectId, name: str, actor_id: PydanticObjectId, **kwargs) -> Product:
    return await ProductService.create_product(
        product_data=ProductCreate(name=name, **kwargs),
        actor_id=actor_id,
        business_id=bid,
    )


def _headers():
    return {"Authorization": "Bearer fake_token"}


# ---------------------------------------------------------------------------
# GET /products (listar)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_products_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_list@example.com", Role.PROPIETARIO, business_id=bid)
    await _make_product(bid, "Monitor 27", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get("/api/v1/products", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_products_denegado_sin_permiso(async_client):
    user = await _make_user("prod_vend@example.com", Role.VENDEDOR)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get("/api/v1/products", headers=_headers())

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /products/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_product_por_id_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_get@example.com", Role.PROPIETARIO, business_id=bid)
    prod = await _make_product(bid, "Teclado Mecánico Get", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get(f"/api/v1/products/{prod.id}", headers=_headers())

    assert resp.status_code == 200
    assert resp.json()["name"] == "Teclado Mecánico Get"


@pytest.mark.asyncio
async def test_get_product_no_existente_retorna_404(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_404@example.com", Role.PROPIETARIO, business_id=bid)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get(f"/api/v1/products/{PydanticObjectId()}", headers=_headers())

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /products/slug/{slug}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_product_por_slug_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_slug@example.com", Role.PROPIETARIO, business_id=bid)
    prod = await _make_product(bid, "Producto Slug Ruta", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get(f"/api/v1/products/slug/{prod.slug}", headers=_headers())

    assert resp.status_code == 200
    assert resp.json()["slug"] == prod.slug


# ---------------------------------------------------------------------------
# POST /products
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_product_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_create@example.com", Role.PROPIETARIO, business_id=bid)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.post(
            "/api/v1/products",
            json={"name": "Nuevo Producto Ruta", "sale_price": 99.9},
            headers=_headers(),
        )

    assert resp.status_code == 201
    assert resp.json()["name"] == "Nuevo Producto Ruta"
    assert resp.json()["images"] == []


@pytest.mark.asyncio
async def test_create_product_denegado_para_almacen(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_alm@example.com", Role.ALMACEN, business_id=bid)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.post(
            "/api/v1/products",
            json={"name": "Producto Bloqueado"},
            headers=_headers(),
        )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /products/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_product_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_upd@example.com", Role.PROPIETARIO, business_id=bid)
    prod = await _make_product(bid, "Producto Viejo Ruta", user.id, sale_price=50.0)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.patch(
            f"/api/v1/products/{prod.id}",
            json={"sale_price": 75.0},
            headers=_headers(),
        )

    assert resp.status_code == 200
    assert resp.json()["sale_price"] == 75.0


# ---------------------------------------------------------------------------
# POST /products/{id}/images
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_product_image_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_img@example.com", Role.PROPIETARIO, business_id=bid)
    prod = await _make_product(bid, "Producto Con Imagen Ruta", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        with patch(
            "app.domains.products.services.CloudinaryService.upload_image",
            new_callable=AsyncMock,
            return_value="https://cdn.io/ruta_img.jpg",
        ):
            resp = await async_client.post(
                f"/api/v1/products/{prod.id}/images",
                files={"file": ("test.jpg", b"fake_bytes", "image/jpeg")},
                headers=_headers(),
            )

    assert resp.status_code == 200
    assert "https://cdn.io/ruta_img.jpg" in resp.json()["images"]


# ---------------------------------------------------------------------------
# DELETE /products/{id}/images
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_product_image_exitoso(async_client):
    bid = PydanticObjectId()
    user = await _make_user("prod_del_img@example.com", Role.PROPIETARIO, business_id=bid)
    prod = await ProductService.create_product(
        product_data=ProductCreate(
            name="Producto Imagen Eliminar Ruta",
            images=["https://cdn.io/eliminar.jpg"],
        ),
        actor_id=user.id,
        business_id=bid,
    )

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        with patch(
            "app.domains.products.services.CloudinaryService.delete_image",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await async_client.delete(
                f"/api/v1/products/{prod.id}/images",
                params={"image_url": "https://cdn.io/eliminar.jpg"},
                headers=_headers(),
            )

    assert resp.status_code == 200
    assert "https://cdn.io/eliminar.jpg" not in resp.json()["images"]


# ---------------------------------------------------------------------------
# DELETE /products/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_product_exitoso(async_client):
    bid = PydanticObjectId()
    superadmin = await _make_user("prod_del_super@example.com", Role.SUPERADMIN)
    propietario = await _make_user("prod_del_owner@example.com", Role.PROPIETARIO, business_id=bid)
    prod = await _make_product(bid, "Producto A Eliminar Ruta", propietario.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(superadmin.id)}):
        resp = await async_client.delete(
            f"/api/v1/products/{prod.id}?business_id={bid}",
            headers=_headers(),
        )

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_product_denegado_para_finanzas(async_client):
    bid = PydanticObjectId()
    user = await _make_user("finanzas_del@example.com", Role.FINANZAS, business_id=bid)
    prod = await _make_product(bid, "Prod Finanzas Del", user.id)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.delete(
            f"/api/v1/products/{prod.id}",
            headers=_headers(),
        )

    assert resp.status_code == 403
