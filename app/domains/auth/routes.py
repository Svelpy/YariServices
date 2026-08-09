from app.core.config import Settings, get_settings
from fastapi import APIRouter, Depends, Request, Response, status
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from app.middlewares.limiter import limiter
from app.domains.auth.schemas import UserSelfRegister, UserLogin, TokenResponse
from app.domains.auth.services import AuthService
from app.domains.users import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(user_data: UserSelfRegister):

    """Registro público de nuevos usuarios.
    
    Crea una cuenta con rol 'USER' y estado 'ACTIVE'."""
 
    return await AuthService.register_self(user_data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    """
    Iniciar sesión con correo y contraseña.
    
    Emite un token JWT de acceso válido.
    """
    credentials = UserLogin(email=form_data.username,password=form_data.password)
    tokens = await AuthService.login(credentials, settings)
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    return TokenResponse(
        access_token=tokens.access_token,
        token_type="bearer",
    )

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    refresh_token = request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )

    tokens = await AuthService.refresh(
        refresh_token,
        settings,
    )

    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=tokens.refresh_token,
        httponly=True,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=tokens.access_token,
        token_type="bearer",
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    refresh_token = request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )

    await AuthService.logout(refresh_token)

    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth",
    )



