from app.domains.auth.schemas import CurrentUser
from beanie import PydanticObjectId
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

from app.domains.auth.schemas import TokenClaims
from app.core.repositories import TenantRepository
from app.core.security import decode_access_token
from app.core.config import Settings, get_settings
from app.shared.enums import Action, Module, Role, UserStatus, BillingStatus
from app.shared.services.permissions import PLATFORM_ROLES, has_permission
from app.domains.users import User
from app.domains.bussines.models import Business


# auto_error=False permite que el header sea opcional (para endpoints públicos)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login",auto_error=False)

def _get_token_claims(token: str | None,settings: Settings) -> TokenClaims:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token de autenticación requerido",headers={"WWW-Authenticate": "Bearer"})

    payload = decode_access_token(token, settings)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token inválido",headers={"WWW-Authenticate": "Bearer"})

    try:
        return TokenClaims.model_validate(payload)
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token inválido",headers={"WWW-Authenticate": "Bearer"})



async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings=Depends(get_settings)) -> User:

    claims = _get_token_claims(token, settings)

    user = await User.get(claims.sub)
    if user is None or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token invalido",headers={"WWW-Authenticate": "Bearer"})

    if user.status != UserStatus.ACTIVE or not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Usuario inactivo o no verificado" )

    if user.role not in PLATFORM_ROLES:
        if user.business_id is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="El usuario no tiene un negocio asignado.")

        business = await Business.get(user.business_id)
        if business is None or business.is_deleted:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="El negocio no esta disponible.")

        if not business.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="El negocio esta inactivo.")

        if business.billing_status == BillingStatus.SUSPENDED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El acceso está suspendido por falta de pago.")
        if business.billing_status == BillingStatus.CANCELED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La suscripción del negocio está cancelada.")
    
    return user

async def get_current_principal( user: User = Depends(get_current_user)) -> CurrentUser:
    return CurrentUser(id=user.id,role=user.role,business_id=user.business_id)

async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    settings: Settings=Depends(get_settings)) -> User | None:
    if token is None:
        return None
    return await get_current_user(token, settings)

async def get_current_principal_optional(user: User | None = Depends(get_current_user_optional)) -> CurrentUser | None:
    if user is None:
        return None
    return CurrentUser(id=user.id,role=user.role,business_id=user.business_id)




def require_roles(*allowed_roles: Role):
    async def dependency(current_user: CurrentUser = Depends(get_current_principal)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="No tenés permisos para realizar esta acción")
        return current_user
    return dependency


def require_permission(module: Module, action: Action):
    async def dependency(current_user: CurrentUser = Depends(get_current_principal)) -> CurrentUser:
        if not has_permission(current_user.role, module, action):#estudia has_perssion
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="No tenés permisos para realizar esta acción" )
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="El business_id es obligatorio para usuarios de plataforma.")
        return business_id

    if business_id is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Los usuarios de negocio no pueden especificar business_id.")

    if current_user.business_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="El usuario no tiene un negocio asignado.")

    return current_user.business_id


def create_repo(model):
    async def dependency(business_id: PydanticObjectId = Depends(resolve_authorized_business_id)):
        return TenantRepository(model, business_id)
    return dependency
