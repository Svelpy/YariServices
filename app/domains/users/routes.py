from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pymongo import AsyncMongoClient

from app.core.config import Settings, get_settings
from app.core.database import get_mongodb_client
from app.core.repositories import BaseRepository, TenantRepository
from app.shared.enums import Action, Module, Role, UserStatus
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth.dependencies import (
    get_current_user,
    require_platform_permission,
    require_tenant_permission,
)
from app.domains.auth import CurrentUser
from app.domains.bussines.dependencies import get_business_repository
from app.domains.bussines.models import Business
from app.domains.users.dependencies import (
    get_current_tenant_user_repository,
    get_global_user_repository,
    get_selected_tenant_user_repository,
)
from app.domains.users.models import User
from app.domains.users.schemas import (
    AdminResetPassword,
    PasswordSelfUpdate,
    UserCreate,
    UserResponse,
    UserResponseAudit,
    UserSelfUpdate,
    UserUpdate,
    UserCreationResponse,
)
from app.domains.users.services import (
    PlatformUserService,
    TenantUserService,
    UserSelfService,
)


tenant_router = APIRouter(prefix="/users", tags=["Tenant Users Management"])
platform_router = APIRouter(prefix="/platform/users",tags=["Platform Users Management"])
platform_business_users_router = APIRouter(prefix="/businesses/{business_id}/users",tags=["Platform Business Users Management"])
me_router = APIRouter(prefix="/me",tags=["My Profile"])

# ---------------------------------------------------------------------------
# RUTAS para usuarios de tenants
# ---------------------------------------------------------------------------


@tenant_router.post("", response_model=UserCreationResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.USERS, Action.CREATE)),
    repository: TenantRepository[User] = Depends(get_current_tenant_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
    mongodb_client: AsyncMongoClient = Depends(get_mongodb_client),
    settings: Settings = Depends(get_settings),
):
    """Crea un nuevo usuario dentro del tenant autorizado."""
    created_user = await TenantUserService.create_tenant_user(
        repository=repository,
        global_repository=global_repository,
        user_data=user_data,
        actor=current_user,
        mongodb_client=mongodb_client,
        settings=settings,
    )

    return created_user



@tenant_router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None,description="Búsqueda de texto en nombre, apellido, email o username"),
    role: Role | None = Query(None, description="Filtrar por rol"),
    status: UserStatus | None = Query(None, description="Filtrar por estado del usuario"),
    _: CurrentUser= Depends(require_tenant_permission(Module.USERS, Action.READ)),
    repository: TenantRepository[User] = Depends(get_current_tenant_user_repository),
):
    """Lista usuarios del tenant autorizado con filtros y paginación."""
    return await TenantUserService.list_tenant_users(
        repository=repository,
        page=page,
        per_page=per_page,
        q=q,
        role=role,
        user_status=status,
    )


@tenant_router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: PydanticObjectId,
    _: CurrentUser= Depends(require_tenant_permission(Module.USERS, Action.READ)),
    repository: TenantRepository[User] = Depends(get_current_tenant_user_repository),
):
    """Obtiene un usuario por ID dentro del tenant autorizado."""
    return await TenantUserService.get_tenant_user(
        repository=repository,
        user_id=user_id,
    )


@tenant_router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: PydanticObjectId,
    update_data: UserUpdate,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.USERS, Action.UPDATE)),
    repository: TenantRepository[User] = Depends(get_current_tenant_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Edita la información administrativa de un usuario."""
    return await TenantUserService.update_tenant_user(
        repository=repository,
        global_repository=global_repository,
        user_id=user_id,
        update_data=update_data,
        actor=current_user,
    )


@tenant_router.post("/{user_id}/password")
async def reset_password(
    user_id: PydanticObjectId,
    body: AdminResetPassword,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.USERS, Action.UPDATE)),
    repository: TenantRepository[User] = Depends(get_current_tenant_user_repository),
):
    """Restablece la contraseña de un usuario."""
    await TenantUserService.reset_tenant_user_password(
        repository=repository,
        user_id=user_id,
        data=body,
        actor=current_user,
    )
    return {"detail": "Contraseña restablecida exitosamente"}


@tenant_router.delete("/{user_id}")
async def delete_user(
    user_id: PydanticObjectId,
    current_user: CurrentUser = Depends(require_tenant_permission(Module.USERS, Action.DELETE)),
    repository: TenantRepository[User] = Depends(get_current_tenant_user_repository),
):
    """Elimina un usuario."""
    await TenantUserService.delete_tenant_user(
        repository=repository,
        user_id=user_id,
        actor=current_user,
    )
    return {"detail": "Usuario eliminado exitosamente"}

# ---------------------------------------------------------------------------
# RUTAS DE AUTOGESTIÓN (/me)
# ---------------------------------------------------------------------------


@me_router.get("", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Obtiene la información del perfil autenticado."""
    return current_user


@me_router.patch("", response_model=UserResponse)
async def update_profile(
    data: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Actualiza los datos personales del usuario autenticado."""
    return await UserSelfService.update_my_profile(
        repository=repository,
        update_data=data,
        actor=current_user,
    )


@me_router.post("/password")
async def change_password(
    data: PasswordSelfUpdate,
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Permite al usuario autenticado cambiar su contraseña."""
    await UserSelfService.change_my_password(
        repository=repository,
        user=current_user,
        data=data,
    )
    return {"detail": "Contraseña actualizada exitosamente"}


@me_router.post("/avatar", response_model=UserResponse)
async def update_avatar_self(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Permite al usuario autenticado subir o actualizar su avatar."""
    return await UserSelfService.update_my_avatar(
        repository=repository,
        file=file,
        actor=current_user,
    )

# ---------------------------------------------------------------------------
# RUTAS DE USUARIOS TENANT ADMINISTRADAS DESDE PLATAFORMA
# ---------------------------------------------------------------------------


@platform_business_users_router.post("",response_model=UserCreationResponse,status_code=status.HTTP_201_CREATED)
async def create_business_user(
    business_id: PydanticObjectId,
    user_data: UserCreate,
    current_user: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.CREATE)),
    repository: TenantRepository[User] = Depends(get_selected_tenant_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
    business_repository: BaseRepository[Business] = Depends(get_business_repository),
    mongodb_client: AsyncMongoClient = Depends(get_mongodb_client),
    settings: Settings = Depends(get_settings),
):
    """Crea un usuario tenant dentro del negocio seleccionado."""
    return await PlatformUserService.create_business_user(
        repository=repository,
        global_repository=global_repository,
        business_repository=business_repository,
        business_id=business_id,
        user_data=user_data,
        actor=current_user,
        mongodb_client=mongodb_client,
        settings=settings,
    )


@platform_business_users_router.get("",response_model=PaginatedResponse[UserResponseAudit])
async def list_business_users(
    business_id: PydanticObjectId,
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None,description="Búsqueda de texto en nombre, apellido, email o username"),
    role: Role | None = Query(None, description="Filtrar por rol tenant"),
    status: UserStatus | None = Query(None, description="Filtrar por estado"),
    _: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.READ)),
    repository: TenantRepository[User] = Depends(get_selected_tenant_user_repository),
    business_repository: BaseRepository[Business] = Depends(get_business_repository),
):
    """Lista los usuarios tenant del negocio seleccionado."""
    return await PlatformUserService.list_business_users(
        repository=repository,
        business_repository=business_repository,
        business_id=business_id,
        page=page,
        per_page=per_page,
        q=q,
        role=role,
        user_status=status,
    )


# ---------------------------------------------------------------------------
# RUTAS ADMINISTRATIVAS DE USUARIOS DE PLATAFORMA
# ---------------------------------------------------------------------------


@platform_router.post(
    "",
    response_model=UserCreationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_platform_user(
    user_data: UserCreate,
    current_user: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.CREATE)),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
    mongodb_client: AsyncMongoClient = Depends(get_mongodb_client),
    settings: Settings = Depends(get_settings),
):
    """Crea exclusivamente un usuario de plataforma."""
    return await PlatformUserService.create_platform_user(
        repository=repository,
        global_repository=global_repository,
        user_data=user_data,
        actor=current_user,
        mongodb_client=mongodb_client,
        settings=settings,
    )


@platform_router.get("",response_model=PaginatedResponse[UserResponseAudit])
async def list_platform_users(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None,description="Búsqueda de texto en nombre, apellido, email o username"),
    role: Role | None = Query(None, description="Filtrar por rol"),
    status: UserStatus | None = Query(None, description="Filtrar por estado"),
    _: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.READ)),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Lista exclusivamente usuarios de plataforma."""
    return await PlatformUserService.list_platform_users(
        repository=repository,
        page=page,
        per_page=per_page,
        q=q,
        role=role,
        user_status=status,
    )


@platform_router.get("/{user_id}", response_model=UserResponseAudit)
async def get_platform_user(
    user_id: PydanticObjectId,
    _: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.READ)),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Obtiene cualquier usuario mediante el alcance global de plataforma."""
    return await PlatformUserService.get_platform_user(repository=repository,user_id=user_id)


@platform_router.patch("/{user_id}", response_model=UserResponseAudit)
async def update_platform_user(
    user_id: PydanticObjectId,
    update_data: UserUpdate,
    current_user: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.UPDATE)),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Actualiza administrativamente cualquier usuario autorizado."""
    return await PlatformUserService.update_platform_user(
        repository=repository,
        global_repository=global_repository,
        user_id=user_id,
        update_data=update_data,
        actor=current_user,
    )


@platform_router.post("/{user_id}/password")
async def reset_platform_user_password(
    user_id: PydanticObjectId,
    body: AdminResetPassword,
    current_user: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.UPDATE)),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Restablece la contraseña de cualquier usuario autorizado."""
    await PlatformUserService.reset_platform_user_password(
        repository=repository,
        user_id=user_id,
        data=body,
        actor=current_user,
    )
    return {"detail": "Contraseña restablecida exitosamente"}


@platform_router.delete("/{user_id}")
async def delete_platform_user(
    user_id: PydanticObjectId,
    current_user: CurrentUser = Depends(require_platform_permission(Module.USERS, Action.DELETE)),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
    hard_delete: bool = Query(False, description="Realiza el borrado físico del usuario"),
):
    """Realiza el borrado lógico o físico de cualquier usuario autorizado."""
    await PlatformUserService.delete_platform_user(
        repository=repository,
        user_id=user_id,
        hard_delete=hard_delete,
        actor=current_user,
    )
    return {"detail": "Usuario eliminado exitosamente"}
