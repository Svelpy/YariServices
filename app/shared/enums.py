from enum import Enum

class Role(str, Enum):
# --- Plataforma: tu equipo, no un negocio cliente ---
    SUPERADMIN = "SUPERADMIN"    # Control total, sin restricciones
    ADMIN = "ADMIN"              # Tu equipo, operativo, no puede eliminar
 
    # --- Negocio: usuarios de las empresas clientes ---
    PROPIETARIO = "PROPIETARIO"  # Dueño de la empresa
    GERENTE = "GERENTE"          # Supervisión: reportes, aprobaciones, gestiona staff
    FINANZAS = "FINANZAS"        # Ve costos/márgenes/reportes financieros; no gestiona staff
    VENDEDOR = "VENDEDOR"        # Vende, crea órdenes, ve stock (sin ver costos)
    ALMACEN = "ALMACEN"          # Gestiona stock/recepción; sin ver precios ni reportes
    USER = "USER" 

class Module(str, Enum):
    # --- Fase 1 ---
    BUSINESS = "business"
    USERS = "users"
    CATEGORY = "category"
    PRODUCTS = "products"              # Sin permisos operativos asignados aún

class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
class AuthProvider(str, Enum):
    LOCAL = "LOCAL"
    GOOGLE = "GOOGLE"
    GITHUB = "GITHUB"
    APPLE = "APPLE"

class UserStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"
