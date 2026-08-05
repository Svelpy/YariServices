"""
Tests de integración para las rutas del dominio products.
Tipo: Integration (usa BD de prueba y simula la decodificación del JWT).
"""

from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId

from app.core.repositories import TenantRepository
from app.domains.products.models import Product
from app.domains.products.schemas import ProductCreate
from app.domains.products.services import ProductService
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


def _repo(business_id: PydanticObjectId) -> TenantRepository[Product]:
    return TenantRepository(Product, business_id)


async def _make_product(
    business_id: PydanticObjectId,
    name: str,
    actor_id: PydanticObjectId,
    **kwargs,
) -> Product:
    return await ProductService.create_product(
        repository=_repo(business_id),
        product_data=ProductCreate(name=name, **kwargs),
        actor_id=actor_id,
    )


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake_token"}


def _decode_token(user: User) -> dict[str, str]:
    return {"user_id": str(user.id)}


@pytest.mark.asyncio
async def test_list_products_exitoso_para_rol_de_tenant(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_list@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    await _make_product(business_id, "Monitor 27", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            "/api/v1/products",
            headers=_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_rol_de_tenant_rechaza_business_id_manual(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_manual_tenant@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            "/api/v1/products",
            params={"business_id": str(business_id)},
            headers=_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rol_de_plataforma_lista_tenant_indicado(async_client):
    business_id = PydanticObjectId()
    admin = await _make_user("prod_admin_list@example.com", Role.ADMIN)
    await _make_product(business_id, "Monitor Plataforma", admin.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.get(
            "/api/v1/products",
            params={"business_id": str(business_id)},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_rol_de_plataforma_requiere_business_id(async_client):
    admin = await _make_user("prod_admin_required@example.com", Role.ADMIN)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.get(
            "/api/v1/products",
            headers=_headers(),
        )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_products_denegado_sin_permiso(async_client):
    user = await _make_user("prod_vend@example.com", Role.VENDEDOR)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            "/api/v1/products",
            headers=_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_product_por_id_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_get@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    product = await _make_product(business_id, "Teclado Mecánico Get", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            f"/api/v1/products/{product.id}",
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Teclado Mecánico Get"


@pytest.mark.asyncio
async def test_rol_de_plataforma_obtiene_producto_del_tenant(async_client):
    business_id = PydanticObjectId()
    admin = await _make_user("prod_admin_get@example.com", Role.ADMIN)
    product = await _make_product(business_id, "Producto Admin Get", admin.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.get(
            f"/api/v1/products/{product.id}",
            params={"business_id": str(business_id)},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Producto Admin Get"


@pytest.mark.asyncio
async def test_get_product_no_existente_retorna_404(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_404@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            f"/api/v1/products/{PydanticObjectId()}",
            headers=_headers(),
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_product_por_slug_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_slug@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    product = await _make_product(business_id, "Producto Slug Ruta", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.get(
            f"/api/v1/products/slug/{product.slug}",
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["slug"] == product.slug


@pytest.mark.asyncio
async def test_create_product_exitoso_para_rol_de_tenant(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_create@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.post(
            "/api/v1/products",
            json={
                "name": "Nuevo Producto Ruta",
                "price": 99.9,
                "price_discount": 89.9,
                "stock": 6,
                "display_order": 1,
            },
            headers=_headers(),
        )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Nuevo Producto Ruta"
    assert body["price"] == 99.9
    assert body["stock"] == 6


@pytest.mark.asyncio
async def test_create_product_exitoso_para_rol_de_plataforma(async_client):
    business_id = PydanticObjectId()
    admin = await _make_user("prod_admin_create@example.com", Role.ADMIN)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.post(
            "/api/v1/products",
            params={"business_id": str(business_id)},
            json={"name": "Producto Creado Por Admin", "price": 150.0},
            headers=_headers(),
        )

    assert response.status_code == 201
    assert response.json()["business_id"] == str(business_id)


@pytest.mark.asyncio
async def test_create_product_denegado_para_almacen(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_alm@example.com",
        Role.ALMACEN,
        business_id=business_id,
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.post(
            "/api/v1/products",
            json={"name": "Producto Bloqueado"},
            headers=_headers(),
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_product_exitoso_para_rol_de_tenant(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_upd@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    product = await _make_product(business_id, "Producto Viejo Ruta", user.id, price=50.0)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.patch(
            f"/api/v1/products/{product.id}",
            json={"price": 75.0, "stock": 14},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["price"] == 75.0
    assert response.json()["stock"] == 14


@pytest.mark.asyncio
async def test_update_product_exitoso_para_rol_de_plataforma(async_client):
    business_id = PydanticObjectId()
    admin = await _make_user("prod_admin_update@example.com", Role.ADMIN)
    product = await _make_product(business_id, "Producto Admin Update", admin.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(admin),
    ):
        response = await async_client.patch(
            f"/api/v1/products/{product.id}",
            params={"business_id": str(business_id)},
            json={"price": 275.0},
            headers=_headers(),
        )

    assert response.status_code == 200
    assert response.json()["price"] == 275.0


@pytest.mark.asyncio
async def test_upload_product_image_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_img@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    product = await _make_product(business_id, "Producto Con Imagen Ruta", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        with patch(
            "app.domains.products.services.CloudinaryService.upload_image",
            new_callable=AsyncMock,
            return_value="https://cdn.io/ruta_img.jpg",
        ):
            response = await async_client.post(
                f"/api/v1/products/{product.id}/images",
                files={"file": ("test.jpg", b"fake_bytes", "image/jpeg")},
                headers=_headers(),
            )

    assert response.status_code == 200
    assert "https://cdn.io/ruta_img.jpg" in response.json()["images"]


@pytest.mark.asyncio
async def test_delete_product_image_exitoso(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "prod_del_img@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    product = await _make_product(
        business_id,
        "Producto Imagen Eliminar Ruta",
        user.id,
        images=["https://cdn.io/eliminar.jpg"],
    )

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        with patch(
            "app.domains.products.services.CloudinaryService.delete_image",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await async_client.delete(
                f"/api/v1/products/{product.id}/images",
                params={"image_url": "https://cdn.io/eliminar.jpg"},
                headers=_headers(),
            )

    assert response.status_code == 200
    assert "https://cdn.io/eliminar.jpg" not in response.json()["images"]


@pytest.mark.asyncio
async def test_delete_product_exitoso_para_superadmin(async_client):
    business_id = PydanticObjectId()
    superadmin = await _make_user("prod_del_super@example.com", Role.SUPERADMIN)
    owner = await _make_user(
        "prod_del_owner@example.com",
        Role.PROPIETARIO,
        business_id=business_id,
    )
    product = await _make_product(business_id, "Producto A Eliminar Ruta", owner.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(superadmin),
    ):
        response = await async_client.delete(
            f"/api/v1/products/{product.id}",
            params={"business_id": str(business_id)},
            headers=_headers(),
        )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_product_denegado_para_finanzas(async_client):
    business_id = PydanticObjectId()
    user = await _make_user(
        "finanzas_del@example.com",
        Role.FINANZAS,
        business_id=business_id,
    )
    product = await _make_product(business_id, "Prod Finanzas Del", user.id)

    with patch(
        "app.domains.auth.dependencies.decode_access_token",
        return_value=_decode_token(user),
    ):
        response = await async_client.delete(
            f"/api/v1/products/{product.id}",
            headers=_headers(),
        )

    assert response.status_code == 403
