"""
Tests de integracion para las rutas del dominio category.
Tipo: Integration (usa BD de prueba y simula la decodificacion del JWT).
"""

from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId

from app.core.repositories import TenantRepository
from app.domains.category.models import Category
from app.domains.category.schemas import CategoryCreate
from app.domains.category.services import CategoryService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus


async def _make_user(
    email: str,
    role: Role,
    business_id: PydanticObjectId | None = None,
) -> User:
    user = User(
        email=email,
        role=role,
        status=UserStatus.ACTIVE,
        business_id=business_id,
    )
    await user.save()
    return user


async def _make_category(
    business_id: PydanticObjectId,
    name: str,
    actor_id: PydanticObjectId,
) -> Category:
    return await CategoryService.create_category(
        repository=TenantRepository(Category, business_id),
        category_data=CategoryCreate(name=name),
        actor_id=actor_id,
    )


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake_token"}


@pytest.mark.asyncio
async def test_list_categories_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_list@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    await _make_category(business_id, "Electrónica", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.get(
            "/api/v1/categories",
            headers=_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_categories_rechaza_business_id_manual_para_usuario_de_negocio(
    async_client,
):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_manual_tenant@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.get(
            f"/api/v1/categories?business_id={business_id}",
            headers=_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_categories_denegado_sin_permiso(async_client):
    user = await _make_user("cat_vend@example.com", Role.VENDEDOR)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.get(
            "/api/v1/categories",
            headers=_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_categories_tree_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_tree@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    await _make_category(business_id, "Ropa Tree", user.id)
    await _make_category(business_id, "Camisas Tree", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.get(
            "/api/v1/categories/tree",
            headers=_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_category_por_id_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_get@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    category = await _make_category(business_id, "Alimentos Get", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.get(
            f"/api/v1/categories/{category.id}",
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Alimentos Get"


@pytest.mark.asyncio
async def test_get_category_no_existente_retorna_404(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_404@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.get(
            f"/api/v1/categories/{PydanticObjectId()}",
            headers=_headers(),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_category_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_create@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.post(
            "/api/v1/categories",
            json={"name": "Nueva Categoría"},
            headers=_headers(),
        )

    assert response.status_code == 201
    assert response.json()["name"] == "Nueva Categoría"


@pytest.mark.asyncio
async def test_create_category_denegado_para_almacen(async_client):
    user = await _make_user("cat_alm@example.com", Role.ALMACEN)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.post(
            "/api/v1/categories",
            json={"name": "Intento"},
            headers=_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_category_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "cat_upd@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    category = await _make_category(business_id, "Viejo Nombre Cat", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        response = await async_client.patch(
            f"/api/v1/categories/{category.id}",
            json={"name": "Nuevo Nombre Cat"},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Nuevo Nombre Cat"


@pytest.mark.asyncio
async def test_upload_banner_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "banner_owner@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    category = await _make_category(business_id, "Con Banner Ruta", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(user.id)},
    ):
        with patch(
            "app.domains.category.services.CloudinaryService.upload_image",
            new_callable=AsyncMock,
            return_value="https://cloudinary.com/test.jpg",
        ):
            response = await async_client.post(
                f"/api/v1/categories/{category.id}/banner",
                files={"file": ("test.jpg", b"fake_image_bytes", "image/jpeg")},
                headers=_headers(),
            )

    assert response.status_code == 200
    assert response.json()["banner_url"] == "https://cloudinary.com/test.jpg"


@pytest.mark.asyncio
async def test_delete_category_exitoso(async_client):
    business_id = PydanticObjectId()
    superadmin = await _make_user("cat_del_super@example.com", Role.SUPERADMIN)
    owner = await _make_user(
        "cat_del_owner@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    category = await _make_category(business_id, "Categoria A Borrar Ruta", owner.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value={"user_id": str(superadmin.id)},
    ):
        response = await async_client.delete(
            f"/api/v1/categories/{category.id}?business_id={business_id}",
            headers=_headers(),
        )

    assert response.status_code == 204
