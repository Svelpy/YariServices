"""
Tests de integración para ProductService.
Tipo: Integration (usa BD de prueba real).
"""
import pytest
from unittest.mock import AsyncMock, patch
from beanie import PydanticObjectId

from app.domains.products.models import Product
from app.domains.products.schemas import ProductCreate, ProductUpdate
from app.domains.products.services import ProductService
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


async def _make_product(name: str, bid: PydanticObjectId, actor_id: PydanticObjectId, **kwargs) -> Product:
    return await ProductService.create_product(
        product_data=ProductCreate(name=name, **kwargs),
        actor_id=actor_id,
        business_id=bid,
    )


# ---------------------------------------------------------------------------
# create_product
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_product_exitoso():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Laptop Pro", bid, actor_id, sku="LAP-001", sale_price=1200.0)

    assert prod.name == "Laptop Pro"
    assert prod.slug == "laptop-pro"
    assert prod.sku == "LAP-001"
    assert prod.business_id == bid
    assert prod.sale_price == 1200.0
    assert prod.images == []


@pytest.mark.asyncio
async def test_create_product_con_imagenes():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await ProductService.create_product(
        product_data=ProductCreate(
            name="Teclado RGB",
            images=["https://cdn.io/img1.jpg", "https://cdn.io/img2.jpg"],
        ),
        actor_id=actor_id,
        business_id=bid,
    )
    assert len(prod.images) == 2


@pytest.mark.asyncio
async def test_create_product_slug_duplicado_misma_empresa_lanza_409():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Mouse Inalámbrico", bid, actor_id)

    with pytest.raises(AppException) as exc:
        await _make_product("Mouse Inalámbrico", bid, actor_id)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_product_slug_duplicado_otra_empresa_exitoso():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Teclado", bid_a, actor_id)

    prod_b = await _make_product("Teclado", bid_b, actor_id)
    assert prod_b.slug == "teclado"


@pytest.mark.asyncio
async def test_create_product_sku_duplicado_misma_empresa_lanza_409():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Laptop A", bid, actor_id, sku="DUP-SKU")

    with pytest.raises(AppException) as exc:
        await _make_product("Laptop B", bid, actor_id, sku="DUP-SKU")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_product_barcode_duplicado_misma_empresa_lanza_409():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Producto X", bid, actor_id, barcode="7890001122334")

    with pytest.raises(AppException) as exc:
        await _make_product("Producto Y", bid, actor_id, barcode="7890001122334")
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# get_product
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_product_exitoso():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Auriculares", bid, actor_id)

    found = await ProductService.get_product(prod.id, business_id=bid)
    assert found.id == prod.id
    assert found.name == "Auriculares"


@pytest.mark.asyncio
async def test_get_product_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await ProductService.get_product(PydanticObjectId())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_product_empresa_diferente_lanza_403():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Monitor", bid_a, actor_id)

    with pytest.raises(AppException) as exc:
        await ProductService.get_product(prod.id, business_id=bid_b)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# get_product_by_slug
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_product_by_slug_exitoso():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Silla Gamer", bid, actor_id)

    found = await ProductService.get_product_by_slug(prod.slug, business_id=bid)
    assert found.id == prod.id


@pytest.mark.asyncio
async def test_get_product_by_slug_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await ProductService.get_product_by_slug("slug-que-no-existe", business_id=PydanticObjectId())
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# list_products
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_products_paginacion():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    for i in range(5):
        await _make_product(f"Producto Lista {i}", bid, actor_id)

    result = await ProductService.list_products(business_id=bid, page=1, per_page=3)
    assert result["per_page"] == 3
    assert len(result["data"]) <= 3


@pytest.mark.asyncio
async def test_list_products_filtro_texto():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Impresora Laser", bid, actor_id)
    await _make_product("Escaner Plano", bid, actor_id)

    result = await ProductService.list_products(business_id=bid, q="Impresora")
    assert result["total"] == 1
    assert result["data"][0].name == "Impresora Laser"


@pytest.mark.asyncio
async def test_list_products_aislamiento_por_empresa():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    await _make_product("Solo de Empresa A", bid_a, actor_id)

    result = await ProductService.list_products(business_id=bid_b)
    assert result["total"] == 0


# ---------------------------------------------------------------------------
# update_product
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_product_nombre_recalcula_slug():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Nombre Producto Viejo", bid, actor_id)

    updated = await ProductService.update_product(
        product_id=prod.id,
        update_data=ProductUpdate(name="Nombre Producto Nuevo"),
        actor_id=actor_id,
        business_id=bid,
    )
    assert updated.name == "Nombre Producto Nuevo"
    assert updated.slug == "nombre-producto-nuevo"


@pytest.mark.asyncio
async def test_update_product_precio():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Producto Precio", bid, actor_id, sale_price=100.0)

    updated = await ProductService.update_product(
        product_id=prod.id,
        update_data=ProductUpdate(sale_price=250.0),
        actor_id=actor_id,
        business_id=bid,
    )
    assert updated.sale_price == 250.0


@pytest.mark.asyncio
async def test_update_product_empresa_incorrecta_lanza_403():
    bid_a = PydanticObjectId()
    bid_b = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Producto Protegido", bid_a, actor_id)

    with pytest.raises(AppException) as exc:
        await ProductService.update_product(
            product_id=prod.id,
            update_data=ProductUpdate(name="Intento"),
            actor_id=actor_id,
            business_id=bid_b,
        )
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# delete_product
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_product_soft_delete_exitoso():
    bid = PydanticObjectId()
    actor = await _make_user("del_prod@example.com", Role.PROPIETARIO)
    prod = await _make_product("Producto Eliminar", bid, actor.id)

    await ProductService.delete_product(product_id=prod.id, actor=actor, business_id=bid)

    with pytest.raises(AppException) as exc:
        await ProductService.get_product(prod.id, business_id=bid)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_hard_delete_requiere_superadmin():
    bid = PydanticObjectId()
    gerente = await _make_user("gerente_del_prod@example.com", Role.GERENTE)
    prod = await _make_product("Prod Hard Delete", bid, gerente.id)

    with pytest.raises(AppException) as exc:
        await ProductService.delete_product(
            product_id=prod.id, actor=gerente, business_id=bid, hard_delete=True
        )
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# upload_image / delete_image
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_image_agrega_url_a_lista():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Producto Con Fotos", bid, actor_id)

    mock_file = AsyncMock()
    with patch(
        "app.domains.products.services.CloudinaryService.upload_image",
        new_callable=AsyncMock,
        return_value="https://cdn.io/foto1.jpg",
    ):
        updated = await ProductService.upload_image(
            product_id=prod.id, file=mock_file, actor_id=actor_id, business_id=bid
        )

    assert "https://cdn.io/foto1.jpg" in updated.images


@pytest.mark.asyncio
async def test_delete_image_remueve_url_y_llama_cloudinary():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await ProductService.create_product(
        product_data=ProductCreate(
            name="Producto Con Imagen",
            images=["https://cdn.io/borrar.jpg"],
        ),
        actor_id=actor_id,
        business_id=bid,
    )

    with patch(
        "app.domains.products.services.CloudinaryService.delete_image",
        new_callable=AsyncMock,
        return_value=True,
    ):
        updated = await ProductService.delete_image(
            product_id=prod.id,
            image_url="https://cdn.io/borrar.jpg",
            actor_id=actor_id,
            business_id=bid,
        )

    assert "https://cdn.io/borrar.jpg" not in updated.images


@pytest.mark.asyncio
async def test_create_product_categoria_inexistente_lanza_404():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    fake_cat_id = PydanticObjectId()

    with pytest.raises(AppException) as exc:
        await _make_product("Producto Cat Fake", bid, actor_id, category_id=fake_cat_id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_products_filtro_categoria_e_is_active():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    cat_id = PydanticObjectId()

    p1 = await _make_product("Producto Cat A", bid, actor_id, category_id=cat_id, is_active=True)
    p2 = await _make_product("Producto Sin Cat", bid, actor_id, is_active=True)

    res_cat = await ProductService.list_products(business_id=bid, category_id=cat_id)
    assert res_cat["total"] == 1
    assert res_cat["data"][0].id == p1.id

    res_active = await ProductService.list_products(business_id=bid, is_active=True)
    assert res_active["total"] == 2


@pytest.mark.asyncio
async def test_update_product_barcode_y_sku_y_atributos():
    bid = PydanticObjectId()
    actor_id = PydanticObjectId()
    prod = await _make_product("Laptop Base", bid, actor_id, barcode="111111", sku="SKU-BASE")

    from app.domains.products.schemas import ProductAttributeSchema
    updated = await ProductService.update_product(
        product_id=prod.id,
        update_data=ProductUpdate(
            barcode="222222",
            sku="SKU-NUEVO",
            attributes=[ProductAttributeSchema(key="ram", value="32GB", label="RAM")],
        ),
        actor_id=actor_id,
        business_id=bid,
    )
    assert updated.barcode == "222222"
    assert updated.sku == "SKU-NUEVO"
    assert len(updated.attributes) == 1
    assert updated.attributes[0].key == "ram"


@pytest.mark.asyncio
async def test_delete_product_hard_delete_como_superadmin():
    bid = PydanticObjectId()
    superadmin = await _make_user("super_prod_del@example.com", Role.SUPERADMIN)
    prod = await _make_product("Prod Hard Delete", bid, superadmin.id)

    await ProductService.delete_product(product_id=prod.id, actor=superadmin, business_id=bid, hard_delete=True)

    db_prod = await Product.get(prod.id)
    assert db_prod is None


def test_product_model_repr_and_str():
    bid = PydanticObjectId()
    prod = Product(name="Laptop Dell XPS", slug="laptop-dell-xps", business_id=bid)
    assert repr(prod) == f"<Product Laptop Dell XPS ({bid})>"
    assert str(prod) == "Laptop Dell XPS"

