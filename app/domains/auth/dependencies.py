from app.domains.auth.schemas import CurrentUser
from beanie import PydanticObjectId
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

from app.domains.auth.schemas import TokenClaims
from app.core.repositories import TenantRepository
from app.core.security import decode_access_token
from app.core.config import Settings, get_settings
from app.shared.enums import Action, Module, Role, UserStatus
from app.shared.services.permissions import PLATFORM_ROLES, has_permission
from app.domains.users import User


# auto_error=False permite que el header sea opcional (para endpoints públicos)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login",auto_error=False)

def _get_token_claims(token: str | None,settings: Settings) -> TokenClaims:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token, settings)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return TokenClaims.model_validate(payload)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings=Depends(get_settings)) -> User:
    """
    Obtener usuario actual desde el token JWT.
    Dependency para endpoints protegidos.
    Raises:
        HTTPException 401: Si el token es inválido o el usuario no existe.
        HTTPException 403: Si el usuario existe pero no está activo/verificado.
    """
    claims = _get_token_claims(token, settings)
    user = await User.get(claims.sub)
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

async def get_current_principal(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings)) -> CurrentUser:
    
    claims = _get_token_claims(token, settings)

    return CurrentUser(
        id=claims.sub,
        role=claims.role,
        business_id=claims.business_id,
    )

async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    settings: Settings=Depends(get_settings)) -> User | None:
    """
    Obtener usuario actual si existe, sino retornar None.
    Útil para endpoints que funcionan con o sin autenticación.
    """
    if token is None:
        return None

    return await get_current_user(token, settings)


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
    async def dependency(current_user: CurrentUser = Depends(get_current_principal)) -> CurrentUser:
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
    Retorna directamente el objeto `CurrentUser` autenticado y autorizado.

    Uso:
        current_user: CurrentUser = Depends(require_permission(Module.CATEGORY, Action.READ))
    """
    async def dependency(current_user: CurrentUser = Depends(get_current_principal)) -> CurrentUser:
        if not has_permission(current_user.role, module, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción"
            )
        return current_user

    return dependency


async def resolve_authorized_business_id(
    business_id: PydanticObjectId | None = Query(None,description="ID de la empresa (requerido para roles de plataforma)"),
    current_user: CurrentUser = Depends(get_current_principal),
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
