from fastapi import APIRouter, Request, status
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
async def login(request: Request, credentials: UserLogin):
    """
    Iniciar sesión con correo y contraseña.
    
    Emite un token JWT de acceso válido.
    """
    return await AuthService.login(credentials)







