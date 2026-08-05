"""Tests de integracion para las rutas del dominio Business."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from beanie import PydanticObjectId

from app.domains.bussines.models import Business
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus


async def _make_user(
    email: str,
    role: Role = Role.USER,
    business_id: PydanticObjectId | None = None,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(
        email=email,
        role=role,
        status=status,
        business_id=business_id,
    )
    await user.save()
    return user


async def _make_business(
    name: str,
    slug: str,
    owner: User,
    is_active: bool = True,
) -> Business:
    now = datetime.now(timezone.utc)
    business = Business(
        name=name,
        slug=slug,
        owner_id=owner.id,
        plan_started_at=now,
        plan_expires_at=now + timedelta(days=365),
        is_active=is_active,
    )
    await business.save()

    owner.business_id = business.id
    owner.role = Role.PROPIETARIO
    await owner.save()
    return business


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake_token"}


def _decode_token(user: User) -> dict[str, str]:
    return {"user_id": str(user.id)}


@pytest.mark.asyncio
async def test_get_my_business_exitoso(async_client):
    owner = await _make_user("route_me_owner@biz.com")
    business = await _make_business("Mi Tienda SA", "mi-tienda-sa", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(owner),
    ):
        response = await async_client.get(
            "/api/v1/businesses/me",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(business.id)
    assert response.json()["name"] == "Mi Tienda SA"


@pytest.mark.asyncio
async def test_get_my_business_exitoso_para_gerente(async_client):
    owner = await _make_user("route_me_manager_owner@biz.com")
    manager = await _make_user("route_me_manager@biz.com", Role.GERENTE)
    business = await _make_business("Negocio del gerente", "negocio-gerente", owner)
    manager.business_id = business.id
    await manager.save()

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(manager),
    ):
        response = await async_client.get(
            "/api/v1/businesses/me",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(business.id)


@pytest.mark.asyncio
async def test_get_my_business_sin_empresa_retorna_404(async_client):
    user = await _make_user("route_me_without_business@biz.com", Role.USER)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            "/api/v1/businesses/me",
            headers=_auth_headers(),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_my_business_rechaza_usuario_inactivo(async_client):
    user = await _make_user(
        "route_me_inactive@biz.com",
        Role.USER,
        status=UserStatus.INACTIVE,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            "/api/v1/businesses/me",
            headers=_auth_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_my_business_exitoso_para_propietario(async_client):
    owner = await _make_user("route_patch_me_owner@biz.com")
    business = await _make_business("Nombre Original", "nombre-original", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(owner),
    ):
        response = await async_client.patch(
            "/api/v1/businesses/me",
            json={"name": "Nombre Actualizado"},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Nombre Actualizado"
    assert response.json()["slug"] == "nombre-actualizado"

    refreshed_business = await Business.get(business.id)
    assert refreshed_business is not None
    assert refreshed_business.updated_by == owner.id


@pytest.mark.asyncio
async def test_patch_my_business_exitoso_para_gerente(async_client):
    owner = await _make_user("route_patch_manager_owner@biz.com")
    manager = await _make_user("route_patch_manager@biz.com", Role.GERENTE)
    business = await _make_business("Negocio Original", "negocio-original", owner)
    manager.business_id = business.id
    await manager.save()

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(manager),
    ):
        response = await async_client.patch(
            "/api/v1/businesses/me",
            json={"description": "Actualización del gerente"},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["description"] == "Actualización del gerente"


@pytest.mark.asyncio
async def test_patch_my_business_rechaza_rol_tenant_inferior(async_client):
    user = await _make_user("route_patch_me_user@biz.com", Role.USER)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.patch(
            "/api/v1/businesses/me",
            json={"description": "Intento no autorizado"},
            headers=_auth_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_my_business_sin_empresa_retorna_404(async_client):
    owner = await _make_user("route_patch_me_without_business@biz.com", Role.PROPIETARIO)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(owner),
    ):
        response = await async_client.patch(
            "/api/v1/businesses/me",
            json={"description": "Sin negocio"},
            headers=_auth_headers(),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_business_by_slug_es_publico(async_client):
    owner = await _make_user("route_public_slug_owner@biz.com")
    await _make_business("Tienda Pública", "tienda-publica", owner)

    response = await async_client.get("/api/v1/businesses/slug/tienda-publica")

    assert response.status_code == 200
    assert response.json()["slug"] == "tienda-publica"


@pytest.mark.asyncio
async def test_get_business_by_slug_inexistente_retorna_404(async_client):
    response = await async_client.get(
        "/api/v1/businesses/slug/slug-que-no-existe-xyz"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_business_exitoso_como_admin(async_client):
    admin = await _make_user("route_create_admin@biz.com", Role.ADMIN)
    owner = await _make_user("route_create_owner@biz.com")

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.post(
            "/api/v1/businesses",
            json={"name": "Empresa Nueva Ruta", "owner_id": str(owner.id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    assert response.json()["name"] == "Empresa Nueva Ruta"


@pytest.mark.asyncio
async def test_create_business_denegado_para_rol_tenant(async_client):
    user = await _make_user("route_create_user@biz.com", Role.PROPIETARIO)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.post(
            "/api/v1/businesses",
            json={"name": "Empresa Bloqueada", "owner_id": str(user.id)},
            headers=_auth_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_businesses_exitoso_como_admin(async_client):
    admin = await _make_user("route_list_admin@biz.com", Role.ADMIN)
    owner = await _make_user("route_list_owner@biz.com")
    await _make_business("Empresa Listada", "empresa-listada", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.get(
            "/api/v1/businesses",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_businesses_denegado_para_propietario(async_client):
    owner = await _make_user("route_list_tenant_owner@biz.com", Role.PROPIETARIO)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(owner),
    ):
        response = await async_client.get(
            "/api/v1/businesses",
            headers=_auth_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_business_por_id_exitoso_como_admin(async_client):
    admin = await _make_user("route_get_admin@biz.com", Role.ADMIN)
    owner = await _make_user("route_get_owner@biz.com")
    business = await _make_business("Empresa por ID", "empresa-por-id", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.get(
            f"/api/v1/businesses/{business.id}",
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(business.id)


@pytest.mark.asyncio
async def test_get_business_por_id_denegado_para_propietario(async_client):
    owner = await _make_user("route_get_tenant_owner@biz.com", Role.PROPIETARIO)
    business = await _make_business("Empresa protegida", "empresa-protegida", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(owner),
    ):
        response = await async_client.get(
            f"/api/v1/businesses/{business.id}",
            headers=_auth_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_business_por_id_exitoso_como_admin(async_client):
    admin = await _make_user("route_update_admin@biz.com", Role.ADMIN)
    owner = await _make_user("route_update_owner@biz.com")
    business = await _make_business("Empresa Vieja", "empresa-vieja", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.patch(
            f"/api/v1/businesses/{business.id}",
            json={"name": "Empresa Nueva"},
            headers=_auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Empresa Nueva"


@pytest.mark.asyncio
async def test_update_business_por_id_denegado_para_propietario(async_client):
    owner = await _make_user("route_update_tenant_owner@biz.com", Role.PROPIETARIO)
    business = await _make_business("Empresa sin editar", "empresa-sin-editar", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(owner),
    ):
        response = await async_client.patch(
            f"/api/v1/businesses/{business.id}",
            json={"name": "Intento"},
            headers=_auth_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_business_exitoso_como_superadmin(async_client):
    superadmin = await _make_user("route_delete_superadmin@biz.com", Role.SUPERADMIN)
    owner = await _make_user("route_delete_owner@biz.com")
    business = await _make_business("Empresa a borrar", "empresa-a-borrar", owner)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(superadmin),
    ):
        response = await async_client.delete(
            f"/api/v1/businesses/{business.id}",
            headers=_auth_headers(),
        )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_business_denegado_para_gerente(async_client):
    manager = await _make_user("route_delete_manager@biz.com", Role.GERENTE)
    owner = await _make_user("route_delete_owner_manager@biz.com")
    business = await _make_business(
        "Empresa protegida para borrar",
        "empresa-protegida-borrar",
        owner,
    )
    manager.business_id = business.id
    await manager.save()

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(manager),
    ):
        response = await async_client.delete(
            f"/api/v1/businesses/{business.id}",
            headers=_auth_headers(),
        )

    assert response.status_code == 403
