from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pymongo import AsyncMongoClient

from app.core.config import Settings, get_settings
from app.core.database import get_mongodb_client
from app.core.repositories import BaseRepository, TenantRepository
from app.shared.enums import Action, Module, Role, UserStatus
from app.shared.schemas.pagination import PaginatedResponse
from app.domains.auth.dependencies import create_repo, get_current_user, require_permission
from app.domains.auth import CurrentUser
from app.domains.users.models import User
from app.domains.users.schemas import (
    AdminResetPassword,
    PasswordSelfUpdate,
    UserCreate,
    UserResponse,
    UserResponseAudit,
    UserSelfUpdate,
    UserUpdate,
)
from app.domains.users.services import UserService


router = APIRouter(prefix="/users", tags=["Users Management"])
get_user_repository = create_repo(User)


def get_global_user_repository() -> BaseRepository[User]:
    """Repositorio global para unicidad y autogestión del usuario."""
    return BaseRepository(User)


# ---------------------------------------------------------------------------
# RUTAS ADMINISTRATIVAS GENERALES
# ---------------------------------------------------------------------------


@router.post("", response_model=UserResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: CurrentUser = Depends(require_permission(Module.USERS, Action.CREATE)),
    repository: TenantRepository[User] = Depends(get_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
    mongodb_client: AsyncMongoClient = Depends(get_mongodb_client),
    settings: Settings = Depends(get_settings),
):
    """Crea un nuevo usuario dentro del tenant autorizado."""
    created_user = await UserService.create_user(
        repository=repository,
        global_repository=global_repository,
        user_data=user_data,
        actor=current_user,
        mongodb_client=mongodb_client,
        settings=settings,
    )

    return created_user



@router.get("", response_model=PaginatedResponse[UserResponseAudit])
async def list_users(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(
        None,
        description="Búsqueda de texto en nombre, apellido, email o username",
    ),
    role: Role | None = Query(None, description="Filtrar por rol"),
    status: UserStatus | None = Query(None, description="Filtrar por estado del usuario"),
    _: CurrentUser= Depends(require_permission(Module.USERS, Action.READ)),
    repository: TenantRepository[User] = Depends(get_user_repository),
):
    """Lista usuarios del tenant autorizado con filtros y paginación."""
    return await UserService.list_users(
        repository=repository,
        page=page,
        per_page=per_page,
        q=q,
        role=role,
        user_status=status,
    )


# ---------------------------------------------------------------------------
# RUTAS DE AUTOGESTIÓN (/me)
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Obtiene la información del perfil autenticado."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Actualiza los datos personales del usuario autenticado."""
    return await UserService.update_profile(
        repository=repository,
        update_data=data,
        actor=current_user,
    )


@router.post("/me/password")
async def change_password(
    data: PasswordSelfUpdate,
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Permite al usuario autenticado cambiar su contraseña."""
    await UserService.change_password(
        repository=repository,
        user=current_user,
        data=data,
    )
    return {"detail": "Contraseña actualizada exitosamente"}


@router.post("/me/avatar", response_model=UserResponse)
async def update_avatar_self(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Permite al usuario autenticado subir o actualizar su avatar."""
    return await UserService.update_avatar_self(
        repository=repository,
        file=file,
        actor=current_user,
    )


# ---------------------------------------------------------------------------
# RUTAS ADMINISTRATIVAS SOBRE UN USUARIO ESPECÍFICO
# ---------------------------------------------------------------------------


@router.get("/{user_id}", response_model=UserResponseAudit)
async def get_user(
    user_id: PydanticObjectId,
    _: CurrentUser= Depends(require_permission(Module.USERS, Action.READ)),
    repository: TenantRepository[User] = Depends(get_user_repository),
):
    """Obtiene un usuario por ID dentro del tenant autorizado."""
    return await UserService.get_user(
        repository=repository,
        user_id=user_id,
    )


@router.patch("/{user_id}", response_model=UserResponseAudit)
async def update_user(
    user_id: PydanticObjectId,
    update_data: UserUpdate,
    current_user: CurrentUser = Depends(require_permission(Module.USERS, Action.UPDATE)),
    repository: TenantRepository[User] = Depends(get_user_repository),
    global_repository: BaseRepository[User] = Depends(get_global_user_repository),
):
    """Edita la información administrativa de un usuario."""
    return await UserService.update_user(
        repository=repository,
        global_repository=global_repository,
        user_id=user_id,
        update_data=update_data,
        actor=current_user,
    )


@router.post("/{user_id}/password")
async def reset_password(
    user_id: PydanticObjectId,
    body: AdminResetPassword,
    current_user: CurrentUser = Depends(require_permission(Module.USERS, Action.UPDATE)),
    repository: TenantRepository[User] = Depends(get_user_repository),
):
    """Restablece la contraseña de un usuario."""
    await UserService.reset_password(
        repository=repository,
        user_id=user_id,
        data=body,
        actor=current_user,
    )
    return {"detail": "Contraseña restablecida exitosamente"}


@router.post("/{user_id}/avatar", response_model=UserResponseAudit)
async def update_avatar(
    user_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission(Module.USERS, Action.UPDATE)),
    repository: TenantRepository[User] = Depends(get_user_repository),
):
    """Actualiza el avatar de un usuario."""
    return await UserService.update_avatar(
        repository=repository,
        user_id=user_id,
        file=file,
        actor=current_user,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: CurrentUser = Depends(require_permission(Module.USERS, Action.DELETE)),
    repository: TenantRepository[User] = Depends(get_user_repository),
):
    """Elimina un usuario."""
    await UserService.delete_user(
        repository=repository,
        user_id=user_id,
        actor=current_user,
        hard_delete=hard_delete,
    )
    return {"detail": "Usuario eliminado exitosamente"}
