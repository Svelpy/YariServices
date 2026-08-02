from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from beanie import Document, before_event, Save, Replace, Update, PydanticObjectId
from pydantic import Field

class BaseDocument(Document):
    """
    Modelo base que extiende Beanie Document.
    Incluye campos de auditoría automática.
    """
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: PydanticObjectId | None = None
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: PydanticObjectId | None = None
    
    is_deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: PydanticObjectId | None = None 

    class Settings:
        # NO usar is_root=True para permitir que cada modelo tenga su propia colección
        use_state_management = True  # Habilita hooks de ciclo de vida que esto es una clase base abstracta
        use_revision=True
    @before_event([Save, Replace, Update])
    def pre_save(self):
        """
        Hook que se ejecuta automáticamente antes de guardar/actualizar.
        Actualiza el campo updated_at y genera nueva revisión.
        """
        self.updated_at = datetime.now(timezone.utc)
        