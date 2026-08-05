"""Tests de integracion para los servicios del dominio Business."""

from datetime import datetime, timedelta, timezone

import pytest
from beanie import PydanticObjectId

from app.core.repositories import BaseRepository
from app.domains.bussines.models import Business
from app.domains.bussines.schemas import BusinessCreate, BusinessMeUpdate, BusinessUpdate
from app.domains.bussines.services import BusinessService
from app.domains.users.models import User
from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException


def _business_repository() -> BaseRepository[Business]:
    return BaseRepository(Business)


def _user_repository() -> BaseRepository[User]:
    return BaseRepository(User)


async def _make_user(
    email: str,
    role: Role = Role.USER,
    business_id: PydanticObjectId | None = None,
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(email=email, role=role, status=status, business_id=business_id)
    await user.save()
    return user


async def _make_business(name: str, owner: User, actor: User) -> Business:
    return await BusinessService.create_business(
        repository=_business_repository(),
        user_repository=_user_repository(),
        data=BusinessCreate(name=name, owner_id=owner.id),
        actor=actor,
    )


@pytest.mark.asyncio
async def test_create_business_exitoso_y_vincula_al_propietario():
    owner = await _make_user("owner@biz.com")
    admin = await _make_user("admin@biz.com", Role.ADMIN)
    business = await _make_business("Ferretería Central", owner, admin)

    assert business.name == "Ferretería Central"
    assert business.slug == "ferreteria-central"
    assert business.owner_id == owner.id

    refreshed_owner = await User.get(owner.id)
    assert refreshed_owner is not None
    assert refreshed_owner.role == Role.PROPIETARIO
    assert refreshed_owner.business_id == business.id


@pytest.mark.asyncio
async def test_create_business_genera_slug():
    owner = await _make_user("slug_owner@biz.com")
    admin = await _make_user("slug_admin@biz.com", Role.ADMIN)
    business = await _make_business("Tecnología & Innovación S.A.", owner, admin)

    assert business.slug == "tecnologia-innovacion-s-a"


@pytest.mark.asyncio
async def test_create_business_rechaza_propietario_duplicado():
    owner = await _make_user("duplicate_owner@biz.com")
    admin = await _make_user("duplicate_admin@biz.com", Role.ADMIN)
    await _make_business("Empresa Uno", owner, admin)

    with pytest.raises(AppException) as exc:
        await _make_business("Empresa Dos", owner, admin)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_business_rechaza_slug_duplicado():
    owner_one = await _make_user("slug_duplicate_one@biz.com")
    owner_two = await _make_user("slug_duplicate_two@biz.com")
    admin = await _make_user("slug_duplicate_admin@biz.com", Role.ADMIN)
    await _make_business("Mi Empresa", owner_one, admin)

    with pytest.raises(AppException) as exc:
        await _make_business("Mi Empresa", owner_two, admin)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_business_rechaza_propietario_inexistente():
    admin = await _make_user("create_missing_owner@biz.com", Role.ADMIN)

    with pytest.raises(AppException) as exc:
        await BusinessService.create_business(
            repository=_business_repository(),
            user_repository=_user_repository(),
            data=BusinessCreate(name="Empresa X", owner_id=PydanticObjectId()),
            actor=admin,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_business_exitoso():
    owner = await _make_user("get_owner@biz.com")
    admin = await _make_user("get_admin@biz.com", Role.ADMIN)
    business = await _make_business("Panadería Los Pinos", owner, admin)

    found = await BusinessService.get_business(_business_repository(), business.id)

    assert found.id == business.id
    assert found.name == "Panadería Los Pinos"


@pytest.mark.asyncio
async def test_get_business_inexistente_retorna_404():
    with pytest.raises(AppException) as exc:
        await BusinessService.get_business(_business_repository(), PydanticObjectId())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_business_by_slug_exitoso():
    owner = await _make_user("slug_get_owner@biz.com")
    admin = await _make_user("slug_get_admin@biz.com", Role.ADMIN)
    business = await _make_business("Ropa Elegante", owner, admin)

    found = await BusinessService.get_business_by_slug(
        _business_repository(),
        business.slug,
    )

    assert found.id == business.id


@pytest.mark.asyncio
async def test_get_business_by_slug_inexistente_retorna_404():
    with pytest.raises(AppException) as exc:
        await BusinessService.get_business_by_slug(
            _business_repository(),
            "slug-que-no-existe-xyz",
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_businesses_pagina_resultados():
    admin = await _make_user("list_admin@biz.com", Role.ADMIN)

    for index in range(3):
        owner = await _make_user(f"list_owner_{index}@biz.com")
        await _make_business(f"Empresa Lista {index}", owner, admin)

    result = await BusinessService.list_businesses(
        _business_repository(),
        page=1,
        per_page=2,
    )

    assert result["per_page"] == 2
    assert len(result["data"]) == 2
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_list_businesses_filtra_por_texto():
    admin = await _make_user("filter_admin@biz.com", Role.ADMIN)
    owner_one = await _make_user("filter_owner_one@biz.com")
    owner_two = await _make_user("filter_owner_two@biz.com")
    await _make_business("Zapatería Moderna", owner_one, admin)
    await _make_business("Panadería Central", owner_two, admin)

    result = await BusinessService.list_businesses(
        _business_repository(),
        q="Zapatería",
    )

    assert [business.name for business in result["data"]] == ["Zapatería Moderna"]


@pytest.mark.asyncio
async def test_list_businesses_filtra_por_estado():
    admin = await _make_user("active_filter_admin@biz.com", Role.ADMIN)
    owner_one = await _make_user("active_owner_one@biz.com")
    owner_two = await _make_user("active_owner_two@biz.com")
    active_business = await _make_business("Empresa Activa", owner_one, admin)
    inactive_business = await _make_business("Empresa Inactiva", owner_two, admin)

    await BusinessService.update_business(
        _business_repository(),
        inactive_business.id,
        BusinessUpdate(is_active=False),
        admin,
    )

    result = await BusinessService.list_businesses(
        _business_repository(),
        is_active=True,
    )
    active_ids = [business.id for business in result["data"]]

    assert active_business.id in active_ids
    assert inactive_business.id not in active_ids


@pytest.mark.asyncio
async def test_update_business_servicio_actualiza_sin_autorizar_rol():
    owner = await _make_user("update_owner@biz.com")
    admin = await _make_user("update_admin@biz.com", Role.ADMIN)
    manager = await _make_user("update_manager@biz.com", Role.GERENTE)
    business = await _make_business("Nombre Viejo", owner, admin)

    updated = await BusinessService.update_business(
        _business_repository(),
        business.id,
        BusinessUpdate(name="Nombre Nuevo"),
        manager,
    )

    assert updated.name == "Nombre Nuevo"
    assert updated.slug == "nombre-nuevo"
    assert updated.updated_by == manager.id


@pytest.mark.asyncio
async def test_update_my_business_como_propietario():
    owner = await _make_user("update_me_owner@biz.com")
    admin = await _make_user("update_me_admin@biz.com", Role.ADMIN)
    business = await _make_business("Nombre Inicial", owner, admin)
    owner = await User.get(owner.id)

    updated = await BusinessService.update_my_business(
        _business_repository(),
        BusinessMeUpdate(description="Descripción actualizada"),
        owner,
    )

    assert updated.id == business.id
    assert updated.description == "Descripción actualizada"
    assert updated.updated_by == owner.id


@pytest.mark.asyncio
async def test_update_my_business_como_gerente():
    owner = await _make_user("update_me_manager_owner@biz.com")
    admin = await _make_user("update_me_manager_admin@biz.com", Role.ADMIN)
    manager = await _make_user("update_me_manager@biz.com", Role.GERENTE)
    business = await _make_business("Negocio del gerente", owner, admin)
    manager.business_id = business.id
    await manager.save()

    updated = await BusinessService.update_my_business(
        _business_repository(),
        BusinessMeUpdate(description="Descripción del gerente"),
        manager,
    )

    assert updated.id == business.id
    assert updated.description == "Descripción del gerente"
    assert updated.updated_by == manager.id


@pytest.mark.asyncio
async def test_update_my_business_sin_tenant_retorna_404():
    user = await _make_user("update_me_without_business@biz.com", Role.PROPIETARIO)

    with pytest.raises(AppException) as exc:
        await BusinessService.update_my_business(
            _business_repository(),
            BusinessMeUpdate(description="Intento"),
            user,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_business_rechaza_slug_duplicado():
    owner_one = await _make_user("update_slug_owner_one@biz.com")
    owner_two = await _make_user("update_slug_owner_two@biz.com")
    admin = await _make_user("update_slug_admin@biz.com", Role.ADMIN)
    await _make_business("Tienda Alfa", owner_one, admin)
    business_two = await _make_business("Tienda Beta", owner_two, admin)

    with pytest.raises(AppException) as exc:
        await BusinessService.update_business(
            _business_repository(),
            business_two.id,
            BusinessUpdate(name="Tienda Alfa"),
            admin,
        )

    assert exc.value.status_code == 409


def test_business_model_repr_and_str():
    now = datetime.now(timezone.utc)
    business = Business(
        name="Mi Negocio S.A.",
        slug="mi-negocio-sa",
        owner_id=PydanticObjectId(),
        plan_started_at=now,
        plan_expires_at=now + timedelta(days=365),
    )

    assert repr(business) == "<Business Mi Negocio S.A. (mi-negocio-sa)>"
    assert str(business) == "Mi Negocio S.A."
