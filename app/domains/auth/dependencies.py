from bson import ObjectId
from beanie import PydanticObjectId
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.repositories import TenantRepository
from app.core.security import decode_access_token
from app.shared.enums import Action, Module, Role, UserStatus
from app.shared.services.permissions import PLATFORM_ROLES, has_permission
from app.domains.users import User


# auto_error=False permite que el header sea opcional (para endpoints públicos)
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Obtener usuario actual desde el token JWT.
    Dependency para endpoints protegidos.
    Raises:
        HTTPException 401: Si el token es inválido o el usuario no existe.
        HTTPException 403: Si el usuario existe pero no está activo/verificado.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await User.get(ObjectId(user_id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo o no verificado"
        )

    return user


async def get_current_user_optional(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> User | None:
    """
    Obtener usuario actual si existe, sino retornar None.
    Útil para endpoints que funcionan con o sin autenticación.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_roles(*allowed_roles: Role):
    """
    Factory de dependency para chequeo de rol PURO (sin módulo, sin tenant).

    Usar SOLO en rutas que no operan sobre un business_id concreto,
    por ejemplo:
        - POST /businesses          (crear empresa, todavía no existe business_id)
        - GET  /businesses          (listar empresas, panel interno)

    Para cualquier ruta que opere sobre datos de una empresa
    (users, category, products, business/{id}) usar require_permission,
    NO esta función — así te asegurás de que también se valide el
    aislamiento por tenant.
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción"
            )
        return current_user

    return dependency


def require_permission(module: Module, action: Action):
    """
    Dependency para verificar permisos (Module + Action).
    Retorna directamente el objeto `User` autenticado y autorizado.

    Uso:
        current_user: User = Depends(require_permission(Module.CATEGORY, Action.READ))
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user.role, module, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción"
            )
        return current_user

    return dependency


async def resolve_authorized_business_id(
    business_id: PydanticObjectId | None = Query(None,description="ID de la empresa (requerido para roles de plataforma)"),
    current_user: User = Depends(get_current_user),
) -> PydanticObjectId:
    """
    Resuelve el tenant autorizado para la solicitud actual.

    - Roles de plataforma (SUPERADMIN y ADMIN): deben indicar el
      `business_id` objetivo en la petición.
    - Roles de negocio: nunca pueden indicar `business_id`; se utiliza el
      tenant asociado al usuario autenticado.

    El `business_id` enviado por un usuario de negocio se rechaza incluso
    cuando coincide con el tenant de su cuenta, para mantener una única
    fuente de contexto y evitar suplantaciones mediante parámetros.
    """
    if current_user.role in PLATFORM_ROLES:
        if business_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El business_id es obligatorio para usuarios de plataforma.",
            )

        return business_id

    if business_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los usuarios de negocio no pueden especificar business_id.",
        )

    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un negocio asignado.",
        )

    return current_user.business_id


def create_repo(model):
    async def dependency(
        business_id: PydanticObjectId = Depends(
            resolve_authorized_business_id
        ),
    ):
        return TenantRepository(model, business_id)

    return dependency
