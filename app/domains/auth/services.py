from app.shared.errors.exceptions import AppException
from app.domains.users import User
from app.domains.auth.schemas import UserSelfRegister, UserLogin, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.shared.enums import Role, UserStatus, AuthProvider

class AuthService:

    @staticmethod
    async def register_self(user_data: UserSelfRegister) -> User:
        """
        Autoregistro público de nuevos usuarios
        
        Args:
            user_data: Datos del usuario a registrar (role = USER por defecto)
            
        Returns:
            Usuario creado
        """
        username = None
        if user_data.username:
            cleaned_username = user_data.username.strip().lower()
            if cleaned_username != "":
                username = cleaned_username

        # Verificar si el email ya existe
        existing_user = await User.find_one(User.email == user_data.email)
        if existing_user:
            raise AppException("El email ya está registrado.",409)
        
        # Verificar si el username ya existe
        if username!=None:
            existing_username = await User.find_one(User.username == username)
            if existing_username:
                raise AppException("El username ya está en uso.",409)
        
        # Crear nuevo usuario
        new_user = User(
            email=user_data.email,
            username=username,
            name=user_data.name,
            lastname=user_data.lastname,
            password_hash=hash_password(user_data.password),
            role=Role.USER,
            status=UserStatus.ACTIVE,
            email_verified=False,
            auth_provider=AuthProvider.LOCAL,
            avatar_url=None,
            phone_number=user_data.phone_number,
            birth_date=user_data.birth_date,
            created_by=None,
            updated_by=None
        )
        
        await new_user.save()
        return new_user

    @staticmethod
    async def login(credentials: UserLogin) -> TokenResponse:
        """
        Autenticar usuario y generar token JWT
        
        Args:
            credentials: Email y contraseña
            
        Returns:
            Token de acceso y datos del usuario
        """
        # Buscar usuario por email
        user = await User.find_one(User.email == credentials.email, User.is_deleted == False)
        
        if not user:
            raise AppException("Email o contraseña incorrectos.",401)
        
        # Verificar contraseña
        if not user.password_hash or not verify_password(credentials.password, user.password_hash):
            raise AppException("Email o contraseña incorrectos.",401)
        
        # Verificar que el usuario esté activo
        if user.status != UserStatus.ACTIVE:
            raise AppException("Usuario inactivo o no verificado.",403)
        # Crear token JWT
        access_token = create_access_token(
            data={
                "user_id": str(user.id),
                "email": user.email,
                
                
            }
        )
        
        # Retorna el TokenResponse (el serializador de FastAPI se encargará del mapeo a UserResponse)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
        )




