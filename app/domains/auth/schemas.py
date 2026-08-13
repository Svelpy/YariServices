from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from beanie import PydanticObjectId
from app.shared.enums import Role

class UserLogin(BaseModel):
    """Schema de entrada para login con email y contraseña"""
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@adamgroup.com.bo",
                "password": "Passw0rd123",
            }
        }
    )


class TokenResponse(BaseModel):
    """Schema de respuesta al autenticarse exitosamente"""
    access_token: str
    token_type: str = "bearer"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "<jwt-access-token>",
                "token_type": "bearer",
            }
        }
    )
class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str

class CurrentUser(BaseModel):
    id: PydanticObjectId
    role: Role
    business_id: PydanticObjectId | None = None

class TokenClaims(BaseModel):
    sub: PydanticObjectId
    role: Role
    business_id: PydanticObjectId | None = None
    iat: datetime
    exp: datetime
    jti: str

class EmailVerificationResponse(BaseModel):
    message: str