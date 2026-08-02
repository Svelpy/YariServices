from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import BaseModel, Field
from enum import Enum
from app.core.base_model import BaseDocument


class MovementType(str, Enum):
    COMPRA = "compra"
    VENTA = "venta"
    AJUSTE_POSITIVO = "ajuste_positivo"
    AJUSTE_NEGATIVO = "ajuste_negativo"
    TRASLADO_SALIDA = "traslado_salida"
    TRASLADO_ENTRADA = "traslado_entrada"


class MovementItem(BaseModel):
    product_id: PydanticObjectId
    batch_id: PydanticObjectId
    quantity: int = Field(gt=0)
    unit_price: float = Field(default=0.0, ge=0)


class Movement(BaseDocument):
    business_id: Indexed(PydanticObjectId)        
    branch_id: Indexed(PydanticObjectId)          
    target_branch_id: PydanticObjectId | None = None 
    type: MovementType
    items: list[MovementItem] = Field(default_factory=list)
    total: float = Field(default=0.0, ge=0)
    motivo: str | None = None                       
    notes: str | None = None

    class Settings:
        name = "movements"
        indexes = [
            IndexModel([("business_id", ASCENDING), ("branch_id", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("business_id", ASCENDING), ("type", ASCENDING)])
        ]

    def __repr__(self):
        return f"<Movement {self.type} - Total: {self.total} ({self.business_id})>"

    def __str__(self):
        return f"{self.type.value} - {self.total}"