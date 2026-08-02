from pydantic import BaseModel, Field
from beanie import Indexed, PydanticObjectId
from pymongo import IndexModel, ASCENDING
from app.core.base_model import BaseDocument  

# --- ESQUEMA AUXILIAR PARA ATRIBUTOS DINÁMICOS ---
class ProductAttribute(BaseModel):
    key: str    # Identificador técnico
    value: str  # Valor real
    label: str  # Nombre visible en el frontend


# --- MODELO DE PRODUCTO (ETAPA 1) ---
class Product(BaseDocument):
    # --- Control de Empresa e Identificación ---
    business_id: Indexed(PydanticObjectId)   # El "Tenant" / Empresa dueña del producto
    barcode: str | None = None              
    sku: str | None = None                   
    slug: Indexed(str)                      
    
    # --- Datos Básicos ---
    name: str                               
    presentation: str | None = None         
    category_id: PydanticObjectId | None = None   #
    brand: str | None = None                 
    description: str | None = None           

    # --- Financieros e Inventario Plano (Etapa 1) ---
    cost: float = Field(default=0.0, ge=0)
    sale_price: float = Field(default=0.0, ge=0)              
    wholesale_price: float | None = Field(default=None, ge=0)    
    min_stock: int = Field(default=5, ge=0)
    

    # --- Galería de Imágenes (Cloudinary) ---
    images: list[str] = Field(default_factory=list)

    # --- Atributos Polimórficos Multi-Rubro ---
    attributes: list[ProductAttribute] = Field(default_factory=list)

    # --- Control ---
    is_active: bool = True

    class Settings:
        name = "products"
        indexes = [
            # Código de barras único por empresa (ignora nulos)
            IndexModel(
                [("business_id", ASCENDING), ("barcode", ASCENDING)], 
                unique=True,
                partialFilterExpression={"barcode": {"$type": "string"}}
            ),

            # slug único por empresa
            IndexModel([("business_id", ASCENDING), ("slug", ASCENDING)], unique=True),

            # sku único por empresa, solo si existe
            IndexModel(
                [("business_id", ASCENDING), ("sku", ASCENDING)],
                unique=True,
                partialFilterExpression={"sku": {"$type": "string"}}
            ),

            # Búsqueda rápida por Empresa y Categoría
            IndexModel([("business_id", ASCENDING), ("category_id", ASCENDING)]),
            
            # Filtros rápidos de activos en el frontend
            IndexModel([("business_id", ASCENDING), ("is_active", ASCENDING)]),
            
            # Búsqueda por cualquier atributo dinámico (multi-rubro)
            IndexModel([
                ("business_id", ASCENDING),
                ("attributes.key", ASCENDING), 
                ("attributes.value", ASCENDING)
            ])
        ]

    def __repr__(self):
        return f"<Product {self.name} ({self.business_id})>"

    def __str__(self):
        return self.name