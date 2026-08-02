from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from beanie import PydanticObjectId
from app.domains.users import User
from app.shared.enums import Role, UserStatus, Module, Action
from app.shared.services.permissions import PLATFORM_ROLES, has_permission
from app.core.security import decode_access_token

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


async def get_current_business_id(
    business_id: PydanticObjectId | None = Query(None, description="ID de la empresa (requerido para roles de plataforma)"),
    current_user: User = Depends(get_current_user),
) -> PydanticObjectId:
    """
    Obtiene y valida el business_id para la solicitud actual.

    - Roles de negocio (PROPIETARIO, GERENTE, etc.): Retorna automáticamente su `current_user.business_id`.
      Si especifican un business_id distinto, responde 403 Forbidden.
    - Roles de plataforma (SUPERADMIN, ADMIN): Exige especificar el `business_id` en la petición.
    """
    if current_user.role in PLATFORM_ROLES:
        if business_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este endpoint requiere especificar el business_id explícitamente"
            )
        return business_id

    if current_user.business_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Todavía no completaste el registro de tu empresa"
        )

    if business_id is not None and business_id != current_user.business_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés acceso a esta empresa"
        )

    return current_user.business_id