"""
Tests de integración para las rutas del dominio bussines.
Tipo: Integration (usa BD de prueba + decode_access_token mockeado).
"""
import pytest
from unittest.mock import patch
from beanie import PydanticObjectId

from app.domains.bussines.models import Business
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_user(email: str, role: Role = Role.USER, business_id=None) -> User:
    u = User(email=email, role=role, status=UserStatus.ACTIVE, business_id=business_id)
    await u.save()
    return u


async def _make_business(name: str, slug: str, owner: User) -> Business:
    biz = Business(name=name, slug=slug, owner_id=owner.id, is_active=True)
    await biz.save()
    owner.business_id = biz.id
    owner.role = Role.PROPIETARIO
    await owner.save()
    return biz


def _auth_headers(user_id: str) -> dict:
    return {"Authorization": "Bearer fake_token"}


# ---------------------------------------------------------------------------
# GET /businesses/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_my_business_exitoso(async_client):
    owner = await _make_user("me_owner@biz.com")
    biz = await _make_business("Mi Tienda SA", "mi-tienda-sa", owner)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(owner.id)}):
        resp = await async_client.get("/api/v1/businesses/me", headers=_auth_headers(str(owner.id)))

    assert resp.status_code == 200
    assert resp.json()["name"] == "Mi Tienda SA"


@pytest.mark.asyncio
async def test_get_my_business_sin_empresa_retorna_404(async_client):
    user = await _make_user("no_biz@biz.com", Role.USER)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(user.id)}):
        resp = await async_client.get("/api/v1/businesses/me", headers=_auth_headers(str(user.id)))

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /businesses/slug/{slug}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_business_by_slug_exitoso(async_client):
    owner = await _make_user("slug_get@biz.com")
    await _make_business("Tienda Slug", "tienda-slug", owner)

    resp = await async_client.get("/api/v1/businesses/slug/tienda-slug")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "tienda-slug"


@pytest.mark.asyncio
async def test_get_business_by_slug_inexistente_retorna_404(async_client):
    resp = await async_client.get("/api/v1/businesses/slug/slug-que-no-existe-xyz")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /businesses (crear empresa)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_business_exitoso_como_admin(async_client):
    admin = await _make_user("admin_create@biz.com", Role.ADMIN)
    future_owner = await _make_user("future_owner_route@biz.com", Role.USER)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(admin.id)}):
        resp = await async_client.post(
            "/api/v1/businesses",
            json={"name": "Empresa Nueva Ruta", "owner_id": str(future_owner.id)},
            headers=_auth_headers(str(admin.id)),
        )

    assert resp.status_code == 201
    assert resp.json()["name"] == "Empresa Nueva Ruta"


@pytest.mark.asyncio
async def test_create_business_denegado_para_vendedor(async_client):
    vendedor = await _make_user("vend_biz@biz.com", Role.VENDEDOR)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(vendedor.id)}):
        resp = await async_client.post(
            "/api/v1/businesses",
            json={"name": "Empresa Bloqueada", "owner_id": str(vendedor.id)},
            headers=_auth_headers(str(vendedor.id)),
        )

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /businesses (listar)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_businesses_como_admin(async_client):
    admin = await _make_user("list_admin@biz.com", Role.ADMIN)
    owner = await _make_user("list_owner@biz.com")
    await _make_business("Empresa Listada", "empresa-listada", owner)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(admin.id)}):
        resp = await async_client.get("/api/v1/businesses", headers=_auth_headers(str(admin.id)))

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_businesses_denegado_para_propietario(async_client):
    owner = await _make_user("prop_list@biz.com", Role.PROPIETARIO)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(owner.id)}):
        resp = await async_client.get("/api/v1/businesses", headers=_auth_headers(str(owner.id)))

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /businesses/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_business_exitoso_como_admin(async_client):
    admin = await _make_user("upd_admin_route@biz.com", Role.ADMIN)
    owner = await _make_user("upd_owner_route@biz.com")
    biz = await _make_business("Empresa Vieja Ruta", "empresa-vieja-ruta", owner)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(admin.id)}):
        resp = await async_client.patch(
            f"/api/v1/businesses/{biz.id}",
            json={"name": "Empresa Nueva Ruta"},
            headers=_auth_headers(str(admin.id)),
        )

    assert resp.status_code == 200
    assert resp.json()["name"] == "Empresa Nueva Ruta"


# ---------------------------------------------------------------------------
# DELETE /businesses/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_business_exitoso_como_superadmin(async_client):
    superadmin = await _make_user("super_del@biz.com", Role.SUPERADMIN)
    owner = await _make_user("del_owner_route@biz.com")
    biz = await _make_business("Empresa A Borrar", "empresa-a-borrar", owner)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(superadmin.id)}):
        resp = await async_client.delete(
            f"/api/v1/businesses/{biz.id}",
            headers=_auth_headers(str(superadmin.id)),
        )

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_business_denegado_para_gerente(async_client):
    gerente = await _make_user("gerente_del@biz.com", Role.GERENTE)
    owner = await _make_user("gerente_del_owner@biz.com")
    biz = await _make_business("Empresa Protegida Route", "empresa-protegida-route", owner)

    with patch("app.domains.auth.dependencies.decode_access_token", return_value={"user_id": str(gerente.id)}):
        resp = await async_client.delete(
            f"/api/v1/businesses/{biz.id}",
            headers=_auth_headers(str(gerente.id)),
        )

    assert resp.status_code == 403
