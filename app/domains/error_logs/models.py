from typing import Optional, Any
from app.core.base_model import BaseDocument
from pymongo import IndexModel, ASCENDING
from beanie import PydanticObjectId

class ErrorLog(BaseDocument):
    status: str = "error"
    message: str                        # Mensaje del error
    stack: str                          # Stack trace / traceback
    
    #Informacion de la peticion
    path: str | None = None         
    method: str | None = None       
    ip_address: str | None = None    
    user_agent: str | None = None    
    
    #Informacion del usuario
    user_id: PydanticObjectId | None = None 

    class Settings:
        name = "errors"
        indexes = [
            IndexModel(
                [("created_at", ASCENDING)],
                expireAfterSeconds=2592000
            )
        ]