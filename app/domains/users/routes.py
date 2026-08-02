from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.shared.enums import Action, Module, Role, UserStatus
from app.shared.schemas.pagination import PaginatedResponse
from app.shared.services.permissions import PLATFORM_ROLES
from app.domains.auth.dependencies import (
    get_current_business_id,
    get_current_user,
    require_permission,
)
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
from app.domains.users.models import User

router = APIRouter(prefix="/users", tags=["Users Management"])


# ─────────────────────────────────────────────
# RUTAS ADMINISTRATIVAS GENERALES
# ─────────────────────────────────────────────

@router.post("", response_model=UserResponseAudit, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission(Module.USERS, Action.CREATE)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Crea un nuevo usuario (Acción Administrativa).
    """
    if user_data.business_id is None and current_user.role not in PLATFORM_ROLES:
        user_data.business_id = business_id
    return await UserService.register_user(user_data=user_data, actor=current_user)


@router.get("", response_model=PaginatedResponse[UserResponseAudit])
async def list_users(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(10, ge=1, le=100, description="Registros por página"),
    q: str | None = Query(None, description="Búsqueda de texto en nombre, apellido, email o username"),
    role: Role | None = Query(None, description="Filtrar por rol"),
    status: UserStatus | None = Query(None, description="Filtrar por estado del usuario"),
    _: User = Depends(require_permission(Module.USERS, Action.READ)),
    business_id: PydanticObjectId = Depends(get_current_business_id),
):
    """
    Lista usuarios de la empresa con filtros y paginación.
    """
    return await UserService.list_users(
        page=page,
        per_page=per_page,
        q=q,
        role=role,
        user_status=status,
        business_id=business_id,
    )


# ─────────────────────────────────────────────
# RUTAS DE AUTOGESTIÓN (/me)
# ─────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Obtener la información del perfil del usuario autenticado.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Permite al usuario autenticado actualizar sus propios datos personales.
    """
    return await UserService.update_profile(update_data=data, actor=current_user)


@router.post("/me/password")
async def change_password(
    data: PasswordSelfUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Permite al usuario autenticado cambiar su contraseña de forma segura.
    """
    return await UserService.change_password(
        user=current_user,
        data=data,
    )


@router.post("/me/avatar", response_model=UserResponse)
async def update_avatar_self(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Permite al usuario autenticado subir o actualizar su propia foto de perfil.
    """
    return await UserService.update_avatar_self(file=file, actor=current_user)


# ─────────────────────────────────────────────
# RUTAS ADMINISTRATIVAS SOBRE UN USUARIO ESPECÍFICO
# ─────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponseAudit)
async def get_user(
    user_id: PydanticObjectId,
    current_user: User = Depends(require_permission(Module.USERS, Action.READ)),
):
    """
    Obtiene los detalles de un usuario por su ID.
    """
    return await UserService.get_user(user_id=user_id, actor=current_user)


@router.patch("/{user_id}", response_model=UserResponseAudit)
async def update_user(
    user_id: PydanticObjectId,
    update_data: UserUpdate,
    current_user: User = Depends(require_permission(Module.USERS, Action.UPDATE)),
):
    """
    Edita la información de un usuario.
    """
    return await UserService.update_user(
        user_id=user_id,
        update_data=update_data,
        actor=current_user,
    )


@router.post("/{user_id}/password")
async def reset_password(
    user_id: PydanticObjectId,
    body: AdminResetPassword,
    current_user: User = Depends(require_permission(Module.USERS, Action.UPDATE)),
):
    """
    Restablece la contraseña de un usuario.
    """
    await UserService.reset_password(
        user_id=user_id,
        data=body,
        actor=current_user,
    )
    return {"detail": "Contraseña restablecida exitosamente"}


@router.post("/{user_id}/avatar", response_model=UserResponseAudit)
async def update_avatar(
    user_id: PydanticObjectId,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(Module.USERS, Action.UPDATE)),
):
    """
    Actualiza la foto de perfil de un usuario.
    """
    return await UserService.update_avatar(
        user_id=user_id,
        file=file,
        actor=current_user,
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: PydanticObjectId,
    hard_delete: bool = Query(False, description="Eliminación permanente"),
    current_user: User = Depends(require_permission(Module.USERS, Action.DELETE)),
):
    """
    Elimina a un usuario.
    """
    await UserService.delete_user(user_id=user_id, actor=current_user, hard_delete=hard_delete)
    return {"detail": "Usuario eliminado exitosamente"}
