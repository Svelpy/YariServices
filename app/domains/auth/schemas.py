from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import datetime

from app.shared.services.validators import validator_names, validator_username, validator_password, validator_phone



class UserSelfRegister(BaseModel):
    """
    Schema para auto-registro público.
    """
    email: EmailStr
    name: str | None= Field(None, min_length=2, max_length=50)
    lastname: str | None= Field(None, min_length=2, max_length=100)
    username: str | None = Field(None, min_length=4, max_length=20)
    phone_number: str | None = Field(None, min_length=6, max_length=16)
    birth_date: datetime | None = None
    password: str = Field(..., min_length=8, max_length=100)
    
    @field_validator('name', 'lastname')
    @classmethod
    def validate_names(cls, v: str) -> str:
        return validator_names(v)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        return validator_username(v)

    @field_validator('phone_number')
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return validator_phone(v)       

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validator_password(v)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "usuario@adamgroup.com.bo",
                "password": "Passw0rd123",
            }
        }
    )



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
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTA3ZjFmNzdiY2Y4NmNkNzk5NDM5MDExIn0.abc123signature",
                "token_type": "bearer",
            }
        }
    )


