import pytest
from beanie import PydanticObjectId

from app.core.repositories import BaseRepository, TenantRepository
from app.domains.auth.schemas import CurrentUser
from app.domains.users.dependencies import (
    get_current_tenant_user_repository,
    get_global_user_repository,
    get_selected_tenant_user_repository,
)
from app.shared.enums import Role
from app.shared.errors.exceptions import AppException


def test_global_user_repository_is_unscoped():
    repository = get_global_user_repository()

    assert isinstance(repository, BaseRepository)
    assert not isinstance(repository, TenantRepository)


@pytest.mark.asyncio
async def test_current_tenant_user_repository_uses_actor_business():
    business_id = PydanticObjectId("507f1f77bcf86cd799439011")
    actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439012"),
        role=Role.PROPIETARIO,
        business_id=business_id,
    )

    repository = await get_current_tenant_user_repository(actor)

    assert isinstance(repository, TenantRepository)
    assert repository.business_id == business_id


@pytest.mark.asyncio
async def test_current_tenant_user_repository_rejects_platform_actor():
    actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439012"),
        role=Role.ADMIN,
        business_id=None,
    )

    with pytest.raises(AppException) as error:
        await get_current_tenant_user_repository(actor)

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_selected_tenant_repository_is_only_available_to_platform():
    business_id = PydanticObjectId("507f1f77bcf86cd799439011")
    platform_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439012"),
        role=Role.ADMIN,
        business_id=None,
    )
    tenant_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439013"),
        role=Role.PROPIETARIO,
        business_id=business_id,
    )

    repository = await get_selected_tenant_user_repository(
        business_id,
        platform_actor,
    )

    assert isinstance(repository, TenantRepository)
    assert repository.business_id == business_id

    with pytest.raises(AppException) as error:
        await get_selected_tenant_user_repository(business_id, tenant_actor)

    assert error.value.status_code == 403
