"""
Tests de integración para ProductService.
Tipo: Integration (usa BD de prueba real con Beanie).
"""

from unittest.mock import AsyncMock, patch

import pytest
from beanie import PydanticObjectId

from app.core.repositories import TenantRepository
from app.domains.category.models import Category
from app.domains.category.schemas import CategoryCreate
from app.domains.category.services import CategoryService
from app.domains.products.models import Product
from app.domains.products.schemas import ProductAttributeSchema, ProductCreate, ProductUpdate
from app.domains.products.services import ProductService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException


def _repo(business_id: PydanticObjectId) -> TenantRepository[Product]:
    return TenantRepository(Product, business_id)


async def _make_user(
    email: str,
    role: Role = Role.PROPIETARIO,
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
    actor_id: PydanticObjectId,
    name: str = "Electrónica",
) -> Category:
    return await CategoryService.create_category(
        repository=TenantRepository(Category, business_id),
        category_data=CategoryCreate(name=name),
        actor_id=actor_id,
    )


async def _make_product(
    name: str,
    business_id: PydanticObjectId,
    actor_id: PydanticObjectId,
    **kwargs,
) -> Product:
    return await ProductService.create_product(
        repository=_repo(business_id),
        product_data=ProductCreate(name=name, **kwargs),
        actor_id=actor_id,
    )


@pytest.mark.asyncio
async def test_create_product_exitoso_con_nuevos_campos():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()

    product = await _make_product(
        "Laptop Pro",
        business_id,
        actor_id,
        sku="LAP-001",
        price=1200.0,
        price_discount=1100.0,
        stock=8,
        display_order=2,
    )

    assert product.name == "Laptop Pro"
    assert product.slug == "laptop-pro"
    assert product.sku == "LAP-001"
    assert product.business_id == business_id
    assert product.price == 1200.0
    assert product.price_discount == 1100.0
    assert product.stock == 8
    assert product.display_order == 2
    assert product.images == []


@pytest.mark.asyncio
async def test_create_product_con_imagenes():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()

    product = await _make_product(
        "Teclado RGB",
        business_id,
        actor_id,
        images=["https://cdn.io/img1.jpg", "https://cdn.io/img2.jpg"],
    )

    assert len(product.images) == 2


@pytest.mark.asyncio
async def test_create_product_slug_duplicado_misma_empresa_lanza_409():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Mouse Inalámbrico", business_id, actor_id)

    with pytest.raises(AppException) as exc:
        await _make_product("Mouse Inalámbrico", business_id, actor_id)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_product_slug_duplicado_otra_empresa_exitoso():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Teclado", business_id_a, actor_id)

    product_b = await _make_product("Teclado", business_id_b, actor_id)

    assert product_b.slug == "teclado"


@pytest.mark.asyncio
async def test_create_product_sku_duplicado_misma_empresa_lanza_409():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Laptop A", business_id, actor_id, sku="DUP-SKU")

    with pytest.raises(AppException) as exc:
        await _make_product("Laptop B", business_id, actor_id, sku="DUP-SKU")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_product_barcode_duplicado_misma_empresa_lanza_409():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Producto X", business_id, actor_id, barcode="7890001122334")

    with pytest.raises(AppException) as exc:
        await _make_product("Producto Y", business_id, actor_id, barcode="7890001122334")

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_get_product_exitoso():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product("Auriculares", business_id, actor_id)

    found = await ProductService.get_product(_repo(business_id), product.id)

    assert found.id == product.id
    assert found.name == "Auriculares"


@pytest.mark.asyncio
async def test_get_product_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await ProductService.get_product(_repo(PydanticObjectId()), PydanticObjectId())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_product_empresa_diferente_lanza_404():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product("Monitor", business_id_a, actor_id)

    with pytest.raises(AppException) as exc:
        await ProductService.get_product(_repo(business_id_b), product.id)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_product_by_slug_exitoso():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product("Silla Gamer", business_id, actor_id)

    found = await ProductService.get_product_by_slug(_repo(business_id), product.slug)

    assert found.id == product.id


@pytest.mark.asyncio
async def test_get_product_by_slug_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await ProductService.get_product_by_slug(
            _repo(PydanticObjectId()),
            "slug-que-no-existe",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_products_paginacion():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    for index in range(5):
        await _make_product(f"Producto Lista {index}", business_id, actor_id)

    result = await ProductService.list_products(_repo(business_id), page=1, per_page=3)

    assert result["per_page"] == 3
    assert len(result["data"]) == 3


@pytest.mark.asyncio
async def test_list_products_filtro_texto():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Impresora Laser", business_id, actor_id)
    await _make_product("Escaner Plano", business_id, actor_id)

    result = await ProductService.list_products(_repo(business_id), q="Impresora")

    assert result["total"] == 1
    assert result["data"][0].name == "Impresora Laser"


@pytest.mark.asyncio
async def test_list_products_aislamiento_por_empresa():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Solo de Empresa A", business_id_a, actor_id)

    result = await ProductService.list_products(_repo(business_id_b))

    assert result["total"] == 0


@pytest.mark.asyncio
async def test_update_product_nombre_recalcula_slug():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product("Nombre Producto Viejo", business_id, actor_id)

    updated = await ProductService.update_product(
        repository=_repo(business_id),
        product_id=product.id,
        update_data=ProductUpdate(name="Nombre Producto Nuevo"),
        actor_id=actor_id,
    )

    assert updated.name == "Nombre Producto Nuevo"
    assert updated.slug == "nombre-producto-nuevo"


@pytest.mark.asyncio
async def test_update_product_nuevos_campos():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product(
        "Producto Precio",
        business_id,
        actor_id,
        price=100.0,
        stock=2,
    )

    updated = await ProductService.update_product(
        repository=_repo(business_id),
        product_id=product.id,
        update_data=ProductUpdate(
            price=250.0,
            price_discount=225.0,
            stock=12,
            display_order=4,
        ),
        actor_id=actor_id,
    )

    assert updated.price == 250.0
    assert updated.price_discount == 225.0
    assert updated.stock == 12
    assert updated.display_order == 4


@pytest.mark.asyncio
async def test_update_product_empresa_incorrecta_lanza_404():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product("Producto Protegido", business_id_a, actor_id)

    with pytest.raises(AppException) as exc:
        await ProductService.update_product(
            repository=_repo(business_id_b),
            product_id=product.id,
            update_data=ProductUpdate(name="Intento"),
            actor_id=actor_id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_soft_delete_exitoso():
    business_id = PydanticObjectId()
    actor = await _make_user("del_prod@example.com", business_id=business_id)
    product = await _make_product("Producto Eliminar", business_id, actor.id)

    await ProductService.delete_product(
        repository=_repo(business_id),
        product_id=product.id,
        actor=actor,
    )

    with pytest.raises(AppException) as exc:
        await ProductService.get_product(_repo(business_id), product.id)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_hard_delete_requiere_superadmin():
    business_id = PydanticObjectId()
    manager = await _make_user("gerente_del_prod@example.com", Role.GERENTE)
    product = await _make_product("Prod Hard Delete", business_id, manager.id)

    with pytest.raises(AppException) as exc:
        await ProductService.delete_product(
            repository=_repo(business_id),
            product_id=product.id,
            actor=manager,
            hard_delete=True,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_upload_image_agrega_url_a_lista():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product("Producto Con Fotos", business_id, actor_id)
    mock_file = AsyncMock()

    with patch(
        "app.domains.products.services.CloudinaryService.upload_image",
        new_callable=AsyncMock,
        return_value="https://cdn.io/foto1.jpg",
    ):
        updated = await ProductService.upload_image(
            repository=_repo(business_id),
            product_id=product.id,
            file=mock_file,
            actor_id=actor_id,
        )

    assert "https://cdn.io/foto1.jpg" in updated.images


@pytest.mark.asyncio
async def test_delete_image_remueve_url_y_llama_cloudinary():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product(
        "Producto Con Imagen",
        business_id,
        actor_id,
        images=["https://cdn.io/borrar.jpg"],
    )

    with patch(
        "app.domains.products.services.CloudinaryService.delete_image",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_delete:
        updated = await ProductService.delete_image(
            repository=_repo(business_id),
            product_id=product.id,
            image_url="https://cdn.io/borrar.jpg",
            actor_id=actor_id,
        )

    assert "https://cdn.io/borrar.jpg" not in updated.images
    mock_delete.assert_awaited_once_with("https://cdn.io/borrar.jpg")


@pytest.mark.asyncio
async def test_create_product_categoria_inexistente_lanza_404():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()

    with pytest.raises(AppException) as exc:
        await _make_product(
            "Producto Cat Fake",
            business_id,
            actor_id,
            category_id=PydanticObjectId(),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_product_categoria_de_otro_tenant_lanza_404():
    business_id_a = PydanticObjectId()
    business_id_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _make_category(business_id_a, actor_id)

    with pytest.raises(AppException) as exc:
        await _make_product(
            "Producto Cat Otro Tenant",
            business_id_b,
            actor_id,
            category_id=category.id,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_products_filtro_categoria_e_is_active():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    category = await _make_category(business_id, actor_id)

    product_with_category = await _make_product(
        "Producto Cat A",
        business_id,
        actor_id,
        category_id=category.id,
        is_active=True,
    )
    await _make_product("Producto Sin Cat", business_id, actor_id, is_active=True)
    await _make_product("Producto Inactivo", business_id, actor_id, is_active=False)

    result_category = await ProductService.list_products(
        _repo(business_id),
        category_id=category.id,
    )
    result_active = await ProductService.list_products(
        _repo(business_id),
        is_active=True,
    )

    assert result_category["total"] == 1
    assert result_category["data"][0].id == product_with_category.id
    assert result_active["total"] == 2


@pytest.mark.asyncio
async def test_update_product_barcode_sku_y_atributos():
    business_id = PydanticObjectId()
    actor_id = PydanticObjectId()
    product = await _make_product(
        "Laptop Base",
        business_id,
        actor_id,
        barcode="111111",
        sku="SKU-BASE",
    )

    updated = await ProductService.update_product(
        repository=_repo(business_id),
        product_id=product.id,
        update_data=ProductUpdate(
            barcode="222222",
            sku="SKU-NUEVO",
            attributes=[
                ProductAttributeSchema(key="ram", value="32GB", label="RAM")
            ],
        ),
        actor_id=actor_id,
    )

    assert updated.barcode == "222222"
    assert updated.sku == "SKU-NUEVO"
    assert len(updated.attributes) == 1
    assert updated.attributes[0].key == "ram"


@pytest.mark.asyncio
async def test_delete_product_hard_delete_como_superadmin():
    business_id = PydanticObjectId()
    superadmin = await _make_user("super_prod_del@example.com", Role.SUPERADMIN)
    product = await _make_product("Prod Hard Delete", business_id, superadmin.id)

    await ProductService.delete_product(
        repository=_repo(business_id),
        product_id=product.id,
        actor=superadmin,
        hard_delete=True,
    )

    assert await _repo(business_id).get(product.id) is None


def test_product_model_repr_and_str():
    business_id = PydanticObjectId()
    product = Product(
        name="Laptop Dell XPS",
        slug="laptop-dell-xps",
        business_id=business_id,
    )

    assert repr(product) == f"<Product Laptop Dell XPS ({business_id})>"
    assert str(product) == "Laptop Dell XPS"
