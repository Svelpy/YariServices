from beanie import Indexed, PydanticObjectId
from app.core.base_model import BaseDocument


class Business(BaseDocument):
    name: str                                       
    slug: Indexed(str, unique=True)                               
    owner_id: Indexed(PydanticObjectId, unique=True) 
    is_active: bool = True

    class Settings:
        name = "businesses"

    def __repr__(self):
        return f"<Business {self.name} ({self.slug})>"

    def __str__(self):
        return self.name