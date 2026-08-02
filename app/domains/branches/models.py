from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from core.base_model import BaseDocument


class Branch(BaseDocument):
    business_id: Indexed(PydanticObjectId)       
    name: str                                     
    address: str | None = None
    is_main: bool = False
    is_active: bool = True

    class Settings:
        name = "branches"
        indexes = [
            IndexModel([("business_id", ASCENDING), ("name", ASCENDING)])
        ]

    def __repr__(self):
        return f"<Branch {self.name} (Business: {self.business_id})>"

    def __str__(self):
        return self.name