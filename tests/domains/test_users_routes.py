import pytest
from beanie import PydanticObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.domains.auth.dependencies import get_current_principal, get_current_user
from app.domains.auth.schemas import CurrentUser
from app.domains.users.dependencies import (
    get_current_tenant_user_repository,
    get_global_user_repository,
)
from app.domains.users.models import User
from app.domains.users.routes import platform_router, router
from app.shared.enums import Role


def make_app() -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    application.include_router(platform_router)
    return application


def make_user(
    email: str,
    role: Role,
    business_id: PydanticObjectId | None = None,
) -> User:
    return User(
        email=email,
        username=email.split("@")[0],
        name="Test",
        lastname="User",
        role=role,
        business_id=business_id,
        password_hash="hashed-password",
    )


async def request(application: FastAPI, method: str, path: str):
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


@pytest.mark.asyncio
async def test_tenant_cannot_access_platform_users():
    application = make_app()
    tenant_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        role=Role.PROPIETARIO,
        business_id=PydanticObjectId("507f1f77bcf86cd799439012"),
    )
    application.dependency_overrides[get_current_principal] = lambda: tenant_actor

    response = await request(application, "GET", "/platform/users")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_platform_cannot_access_tenant_users():
    application = make_app()
    platform_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        role=Role.ADMIN,
        business_id=None,
    )
    application.dependency_overrides[get_current_principal] = lambda: platform_actor

    response = await request(application, "GET", "/users")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_me_is_available_to_platform_user():
    application = make_app()
    platform_user = make_user("platform@example.com", Role.ADMIN)
    application.dependency_overrides[get_current_user] = lambda: platform_user

    response = await request(application, "GET", "/users/me")

    assert response.status_code == 200
    assert response.json()["email"] == "platform@example.com"


@pytest.mark.asyncio
async def test_me_is_available_to_tenant_user():
    application = make_app()
    tenant_user = make_user(
        "tenant@example.com",
        Role.PROPIETARIO,
        PydanticObjectId("507f1f77bcf86cd799439012"),
    )
    application.dependency_overrides[get_current_user] = lambda: tenant_user

    response = await request(application, "GET", "/users/me")

    assert response.status_code == 200
    assert response.json()["email"] == "tenant@example.com"


@pytest.mark.asyncio
async def test_tenant_list_is_scoped_to_authenticated_business(test_db):
    application = make_app()
    tenant_id = PydanticObjectId("507f1f77bcf86cd799439012")
    other_tenant_id = PydanticObjectId("507f1f77bcf86cd799439013")
    tenant_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        role=Role.PROPIETARIO,
        business_id=tenant_id,
    )
    await make_user("inside@example.com", Role.USER, tenant_id).insert()
    await make_user("outside@example.com", Role.USER, other_tenant_id).insert()
    application.dependency_overrides[get_current_principal] = lambda: tenant_actor

    response = await request(application, "GET", "/users")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["data"][0]["email"] == "inside@example.com"


@pytest.mark.asyncio
async def test_platform_list_can_filter_by_business(test_db):
    application = make_app()
    tenant_id = PydanticObjectId("507f1f77bcf86cd799439012")
    other_tenant_id = PydanticObjectId("507f1f77bcf86cd799439013")
    platform_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        role=Role.ADMIN,
        business_id=None,
    )
    await make_user("inside@example.com", Role.USER, tenant_id).insert()
    await make_user("outside@example.com", Role.USER, other_tenant_id).insert()
    application.dependency_overrides[get_current_principal] = lambda: platform_actor

    response = await request(
        application,
        "GET",
        f"/platform/users?business_id={tenant_id}",
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["data"][0]["email"] == "inside@example.com"


@pytest.mark.asyncio
async def test_platform_list_with_unknown_business_returns_empty(test_db):
    application = make_app()
    platform_actor = CurrentUser(
        id=PydanticObjectId("507f1f77bcf86cd799439011"),
        role=Role.ADMIN,
        business_id=None,
    )
    application.dependency_overrides[get_current_principal] = lambda: platform_actor

    response = await request(
        application,
        "GET",
        "/platform/users?business_id=507f1f77bcf86cd799439099",
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
