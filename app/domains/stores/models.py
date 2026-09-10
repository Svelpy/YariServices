from beanie import Indexed
from pydantic import EmailStr

from app.core.base_model import BaseDocument


class Store(BaseDocument):
    # Identidad
    name: str  
    slug: Indexed(str, unique=True)
    description: str | None = None
    logo_url: str | None = None

    # Contacto
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    address_google_maps_url: str | None = None
    # Moneda por defecto
    currency: str = "BOB" 

    is_active: bool = False

    class Settings:
        name = "stores"

    def __repr__(self):
        return f"<Store {self.name} ({self.slug})>"

    def __str__(self):
        return self.name