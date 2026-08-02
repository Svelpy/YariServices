from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.core.logging import get_logger
from app.domains import all_models

logger = get_logger(__name__)
mongodb_client: AsyncIOMotorClient = None


async def connect_to_mongo():
    """Conectar a MongoDB Atlas y inicializar Beanie"""
    global mongodb_client
    
    try:
        logger.info("Conectando a MongoDB Atlas...")
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        
        # Verificar conexión
        await mongodb_client.admin.command('ping')
        logger.info("✅ Conectado exitosamente a MongoDB Atlas")
        
        # Inicializar Beanie con los modelos
        await init_beanie(
            database=mongodb_client[settings.MONGODB_DB_NAME],
            document_models=all_models
        )
        
        logger.info(f"Beanie inicializado con base de datos: {settings.MONGODB_DB_NAME}")
        
    except Exception as e:
        logger.error(f"Error conectando a MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Cerrar conexión a MongoDB"""
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        logger.info("🔌 Conexión a MongoDB cerrada")
