from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from pydantic import Field
from datetime import datetime
from core.base_model import BaseDocument


class Batch(BaseDocument):
    product_id: Indexed(PydanticObjectId)           
    branch_id: Indexed(PydanticObjectId)           
    
    lot_code: str = "LOTE-GRAL"
    expiration_date: datetime | None = None       
    quantity: int = Field(default=0, ge=0)

    class Settings:
        name = "batches"
        indexes = [
            IndexModel([("branch_id", ASCENDING), ("product_id", ASCENDING)]),
            IndexModel([("product_id", ASCENDING), ("expiration_date", ASCENDING)])  # Para búsquedas FEFO
        ]

    def __repr__(self):
        return f"<Batch {self.lot_code} (Product: {self.product_id}, Qty: {self.quantity})>"

    def __str__(self):
        return f"{self.lot_code} - {self.quantity} u."