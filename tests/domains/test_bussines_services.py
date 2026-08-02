"""
Tests de integración para BusinessService.
Tipo: Integration (usa BD de prueba real).
"""
import pytest
from beanie import PydanticObjectId

from app.domains.bussines.models import Business
from app.domains.bussines.schemas import BusinessCreate, BusinessUpdate
from app.domains.bussines.services import BusinessService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

async def _make_user(email: str, role: Role = Role.USER) -> User:
    u = User(email=email, role=role, status=UserStatus.ACTIVE)
    await u.save()
    return u


async def _make_business(name: str, owner: User, actor: User) -> Business:
    data = BusinessCreate(name=name, owner_id=owner.id)
    return await BusinessService.create_business(data=data, actor=actor)


# ---------------------------------------------------------------------------
# create_business
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_business_exitoso():
    owner = await _make_user("owner@biz.com")
    admin = await _make_user("admin@biz.com", Role.ADMIN)

    biz = await _make_business("Ferretería Central", owner, admin)

    assert biz.name == "Ferretería Central"
    assert biz.slug == "ferreteria-central"
    assert biz.owner_id == owner.id

    # El propietario debe quedar promovido y vinculado
    refreshed = await User.get(owner.id)
    assert refreshed.role == Role.PROPIETARIO
    assert refreshed.business_id == biz.id


@pytest.mark.asyncio
async def test_create_business_slug_generado_correctamente():
    owner = await _make_user("slug_owner@biz.com")
    admin = await _make_user("slug_admin@biz.com", Role.ADMIN)

    biz = await _make_business("Tecnología & Innovación S.A.", owner, admin)
    assert biz.slug == "tecnologia-innovacion-s-a"


@pytest.mark.asyncio
async def test_create_business_owner_duplicado_lanza_409():
    owner = await _make_user("dup_owner@biz.com")
    admin = await _make_user("dup_admin@biz.com", Role.ADMIN)

    await _make_business("Empresa Uno", owner, admin)

    with pytest.raises(AppException) as exc:
        await _make_business("Empresa Dos", owner, admin)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_business_slug_duplicado_lanza_409():
    owner1 = await _make_user("slug_dup_owner1@biz.com")
    owner2 = await _make_user("slug_dup_owner2@biz.com")
    admin = await _make_user("slug_dup_admin@biz.com", Role.ADMIN)

    await _make_business("Mi Empresa", owner1, admin)

    with pytest.raises(AppException) as exc:
        await _make_business("Mi Empresa", owner2, admin)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_business_owner_inexistente_lanza_404():
    admin = await _make_user("admin_404@biz.com", Role.ADMIN)
    data = BusinessCreate(name="Empresa X", owner_id=PydanticObjectId())

    with pytest.raises(AppException) as exc:
        await BusinessService.create_business(data=data, actor=admin)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_business
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_business_exitoso():
    owner = await _make_user("get_owner@biz.com")
    admin = await _make_user("get_admin@biz.com", Role.ADMIN)
    created = await _make_business("Panadería Los Pinos", owner, admin)

    found = await BusinessService.get_business(created.id)
    assert found.id == created.id
    assert found.name == "Panadería Los Pinos"


@pytest.mark.asyncio
async def test_get_business_no_existente_lanza_404():
    with pytest.raises(AppException) as exc:
        await BusinessService.get_business(PydanticObjectId())
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# get_business_by_slug
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_business_by_slug_exitoso():
    owner = await _make_user("slug_get@biz.com")
    admin = await _make_user("slug_get_admin@biz.com", Role.ADMIN)
    biz = await _make_business("Ropa Elegante", owner, admin)

    found = await BusinessService.get_business_by_slug(biz.slug)
    assert found.id == biz.id


@pytest.mark.asyncio
async def test_get_business_by_slug_inexistente_lanza_404():
    with pytest.raises(AppException) as exc:
        await BusinessService.get_business_by_slug("slug-que-no-existe-xyz")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# list_businesses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_businesses_paginacion():
    admin = await _make_user("list_admin@biz.com", Role.ADMIN)
    for i in range(3):
        owner = await _make_user(f"list_owner_{i}@biz.com")
        await _make_business(f"Empresa Lista {i}", owner, admin)

    result = await BusinessService.list_businesses(page=1, per_page=2)
    assert result["per_page"] == 2
    assert len(result["data"]) <= 2


@pytest.mark.asyncio
async def test_list_businesses_filtro_texto():
    admin = await _make_user("filter_admin@biz.com", Role.ADMIN)
    owner_a = await _make_user("filter_owner_a@biz.com")
    owner_b = await _make_user("filter_owner_b@biz.com")

    await _make_business("Zapatería Moderna", owner_a, admin)
    await _make_business("Panadería Central", owner_b, admin)

    result = await BusinessService.list_businesses(q="Zapatería")
    names = [b.name for b in result["data"]]
    assert "Zapatería Moderna" in names
    assert "Panadería Central" not in names


# ---------------------------------------------------------------------------
# update_business
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_business_nombre_exitoso():
    owner = await _make_user("upd_owner@biz.com")
    admin = await _make_user("upd_admin@biz.com", Role.ADMIN)
    biz = await _make_business("Nombre Viejo", owner, admin)

    updated = await BusinessService.update_business(
        business_id=biz.id,
        update_data=BusinessUpdate(name="Nombre Nuevo"),
        actor=admin,
    )
    assert updated.name == "Nombre Nuevo"
    assert updated.slug == "nombre-nuevo"


@pytest.mark.asyncio
async def test_update_business_sin_permiso_lanza_403():
    owner = await _make_user("upd_perm_owner@biz.com")
    admin = await _make_user("upd_perm_admin@biz.com", Role.ADMIN)
    intruder = await _make_user("intruder@biz.com", Role.GERENTE)
    biz = await _make_business("Empresa Protegida", owner, admin)

    with pytest.raises(AppException) as exc:
        await BusinessService.update_business(
            business_id=biz.id,
            update_data=BusinessUpdate(name="Intento"),
            actor=intruder,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_business_slug_duplicado_lanza_409():
    owner1 = await _make_user("slug_upd1@biz.com")
    owner2 = await _make_user("slug_upd2@biz.com")
    admin = await _make_user("slug_upd_admin@biz.com", Role.ADMIN)

    await _make_business("Tienda Alfa", owner1, admin)
    biz_b = await _make_business("Tienda Beta", owner2, admin)

    with pytest.raises(AppException) as exc:
        await BusinessService.update_business(
            business_id=biz_b.id,
            update_data=BusinessUpdate(name="Tienda Alfa"),
            actor=admin,
        )
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# delete_business
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_business_soft_delete_exitoso():
    owner = await _make_user("del_owner@biz.com")
    admin = await _make_user("del_admin@biz.com", Role.ADMIN)
    biz = await _make_business("Empresa A Eliminar", owner, admin)

    await BusinessService.delete_business(business_id=biz.id, actor=admin)

    with pytest.raises(AppException) as exc:
        await BusinessService.get_business(biz.id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_business_hard_delete_como_superadmin():
    owner = await _make_user("hard_del_owner@biz.com")
    superadmin = await _make_user("super_admin_del@biz.com", Role.SUPERADMIN)
    biz = await _make_business("Empresa Hard Delete", owner, superadmin)

    await BusinessService.delete_business(business_id=biz.id, actor=superadmin, hard_delete=True)

    db_biz = await Business.get(biz.id)
    assert db_biz is None


@pytest.mark.asyncio
async def test_delete_business_hard_delete_como_admin_lanza_403():
    owner = await _make_user("hard_del_owner_admin@biz.com")
    admin = await _make_user("admin_hard_del@biz.com", Role.ADMIN)
    biz = await _make_business("Empresa Hard Delete Admin", owner, admin)

    with pytest.raises(AppException) as exc:
        await BusinessService.delete_business(business_id=biz.id, actor=admin, hard_delete=True)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_list_businesses_filtro_is_active():
    admin = await _make_user("active_admin@biz.com", Role.ADMIN)
    owner1 = await _make_user("act_owner1@biz.com")
    owner2 = await _make_user("act_owner2@biz.com")

    biz1 = await _make_business("Empresa Activa", owner1, admin)
    biz2 = await _make_business("Empresa Inactiva", owner2, admin)

    await BusinessService.update_business(biz2.id, BusinessUpdate(is_active=False), actor=admin)

    result_active = await BusinessService.list_businesses(is_active=True)
    active_ids = [b.id for b in result_active["data"]]
    assert biz1.id in active_ids
    assert biz2.id not in active_ids


def test_business_model_repr_and_str():
    biz = Business(name="Mi Negocio S.A.", slug="mi-negocio-sa", owner_id=PydanticObjectId())
    assert repr(biz) == "<Business Mi Negocio S.A. (mi-negocio-sa)>"
    assert str(biz) == "Mi Negocio S.A."

