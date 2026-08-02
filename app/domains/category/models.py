from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from app.core.base_model import BaseDocument

class Category(BaseDocument):
    name: str
    slug: Indexed(str)#
    path: Indexed(str)#
    description: str | None = None

    business_id: Indexed(PydanticObjectId) #
    parent_id: PydanticObjectId | None = None 
    level: int
    display_order: int
    
    banner_url: str | None = None
    is_active: bool = True  #
    #SEO
    meta_title: str | None = None  
    meta_description: str | None = None  
    
    class Settings:
        name = "categories"
        indexes = [
            # slug único, pero solo dentro de la misma empresa
            IndexModel([("business_id", ASCENDING), ("slug", ASCENDING)], unique=True),
            # path único, pero solo dentro de la misma empresa
            IndexModel([("business_id", ASCENDING), ("path", ASCENDING)], unique=True),
            # Para listar hijos directos de forma ordenada, dentro de una empresa
            IndexModel([("business_id", ASCENDING), ("parent_id", ASCENDING), ("display_order", ASCENDING)]),
            # Para búsquedas por nivel dentro de una empresa (ej: categorías raíz del menú)
            IndexModel([("business_id", ASCENDING), ("level", ASCENDING)])
        ]
 
    def __repr__(self):
        return f"<Category {self.path} (Lvl: {self.level})>"
 
    def __str__(self):
        return self.name