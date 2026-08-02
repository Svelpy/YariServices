from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from pydantic import EmailStr
from datetime import datetime
from app.core.base_model import BaseDocument
from app.shared.enums import Role, AuthProvider, UserStatus

class User(BaseDocument):
    # --- Datos Básicos ---
    email: Indexed(EmailStr, unique=True)  # Email único e indexado
    name: str | None = None                          # Nombre(s) — obligatorio
    lastname: str | None = None                       # Apellido(s) — obligatorio
    
    username: str | None = None
    phone_number: str | None = None
    birth_date: datetime | None = None 

    avatar_url: str | None = None

    business_id: PydanticObjectId | None = None
    #Auth
    password_hash: str | None = None
    auth_provider: AuthProvider = AuthProvider.LOCAL
    provider_user_id: str | None= None
    email_verified: bool = False
    #Autorizacion  
    role: Role = Role.USER
    status: UserStatus = UserStatus.PENDING_VERIFICATION

    class Settings:
        name = "users" 
        indexes = [
            IndexModel([("username", ASCENDING)], unique=True, partialFilterExpression={"username": {"$type": "string"}}),
            IndexModel([("business_id", ASCENDING)]),
        ]
    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
    
    def __str__(self):
        return self.email
  