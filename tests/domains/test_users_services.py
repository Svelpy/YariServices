from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.domains.auth.schemas import CurrentUser
from app.domains.users.models import User
from app.domains.users.schemas import AdminResetPassword, UserCreate, UserSelfUpdate, UserUpdate
from app.domains.users.services import (
    PlatformUserService,
    TenantUserService,
    UserSelfService,
)
from app.shared.enums import Role, UserStatus
from app.shared.errors.exceptions import AppException


class FakeRepository:
    def __init__(self, document=None, documents=None):
        self.document = document
        self.documents = documents or []
        self.last_filters = None
        self.saved_document = None

    async def get(self, _document_id):
        return self.document

    async def find_one(self, _filters):
        return None

    async def count(self, filters=None):
        self.last_filters = dict(filters or {})
        return len(self.documents)

    async def list(self, filters=None, *, skip=0, limit=None, sort=None):
        self.last_filters = dict(filters or {})
        return self.documents[skip : skip + limit if limit is not None else None]

    async def save(self, document):
        self.saved_document = document
        return document

    async def create(self, document, *, session=None):
        self.document = document
        return document


def make_user(
    user_id="507f1f77bcf86cd799439011",
    email="user@example.com",
    role=Role.USER,
    business_id=None,
    avatar_url=None,
):
    return User(
        id=PydanticObjectId(user_id),
        email=email,
        username="test_user",
        name="Test",
        lastname="User",
        role=role,
        business_id=business_id,
        avatar_url=avatar_url,
        password_hash="hashed-password",
        status=UserStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_tenant_list_uses_tenant_service_and_filters_deleted_users():
    repository = FakeRepository(documents=[make_user()])

    result = await TenantUserService.list_tenant_users(repository)

    assert result["total"] == 1
    assert repository.last_filters["is_deleted"] is False


@pytest.mark.asyncio
async def test_platform_list_uses_global_service_and_optional_business_filter():
    business_id = PydanticObjectId("507f1f77bcf86cd799439012")
    repository = FakeRepository(documents=[make_user(business_id=business_id)])

    result = await PlatformUserService.list_platform_users(
        repository,
        business_id=business_id,
    )

    assert result["total"] == 1
    assert repository.last_filters["business_id"] == business_id


@pytest.mark.asyncio
async def test_tenant_delete_rejects_user_from_another_business():
    target_business_id = PydanticObjectId("507f1f77bcf86cd799439011")
    actor_business_id = PydanticObjectId("507f1f77bcf86cd799439012")
    target = make_user(business_id=target_business_id)
    repository = FakeRepository(document=target)
    actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439013"),
        role=Role.PROPIETARIO,
        business_id=actor_business_id,
    )

    with pytest.raises(AppException) as error:
        await TenantUserService.delete_tenant_user(repository, target.id, actor)

    assert error.value.status_code == 403
    assert repository.saved_document is None


@pytest.mark.asyncio
async def test_platform_update_can_manage_user_from_any_business():
    target_business_id = PydanticObjectId("507f1f77bcf86cd799439011")
    target = make_user(business_id=target_business_id)
    repository = FakeRepository(document=target)
    actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439012"),
        role=Role.ADMIN,
        business_id=None,
    )

    updated = await PlatformUserService.update_platform_user(
        repository=repository,
        global_repository=FakeRepository(),
        user_id=target.id,
        update_data=UserUpdate(name="Updated"),
        actor=actor,
    )

    assert updated.name == "Updated"
    assert repository.saved_document is target


@pytest.mark.asyncio
async def test_platform_create_rejects_nonexistent_business():
    actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439012"),
        role=Role.ADMIN,
        business_id=None,
    )
    user_data = UserCreate(
        email="new@example.com",
        password="Passw0rd123",
        name="New",
        lastname="User",
    )

    with pytest.raises(AppException) as error:
        await PlatformUserService.create_platform_user(
            repository=FakeRepository(),
            global_repository=FakeRepository(),
            user_data=user_data,
            actor=actor,
            mongodb_client=MagicMock(),
            settings=MagicMock(),
            business_id=PydanticObjectId("507f1f77bcf86cd799439099"),
            business_repository=FakeRepository(document=None),
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_self_profile_updates_only_authenticated_user():
    actor = make_user(email="self@example.com")
    repository = FakeRepository()

    updated = await UserSelfService.update_my_profile(
        repository=repository,
        update_data=UserSelfUpdate(name="Updated"),
        actor=actor,
    )

    assert updated.name == "Updated"
    assert repository.saved_document is actor


@pytest.mark.asyncio
async def test_self_avatar_mocks_cloudinary():
    actor = make_user(email="avatar@example.com", avatar_url="old-image")
    repository = FakeRepository()
    upload = AsyncMock(return_value="new-image")
    delete = AsyncMock()

    with (
        patch(
            "app.domains.users.services.CloudinaryService.upload_image",
            upload,
        ),
        patch(
            "app.domains.users.services.CloudinaryService.delete_image",
            delete,
        ),
    ):
        updated = await UserSelfService.update_my_avatar(
            repository=repository,
            file=SimpleNamespace(),
            actor=actor,
        )

    assert updated.avatar_url == "new-image"
    upload.assert_awaited_once()
    delete.assert_awaited_once_with("old-image")
