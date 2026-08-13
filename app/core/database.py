from beanie import init_beanie
from pymongo.asynchronous.database import AsyncDatabase
from fastapi import Request
from pymongo import AsyncMongoClient

from app.core.config import Settings
from app.core.logging import get_logger
from app.domains import all_models


logger = get_logger(__name__)



async def initialize_beanie(database: AsyncDatabase,settings: Settings) -> None:
    """Inicializa Beanie."""

    try:
        
        logger.info("Inicializando Beanie...")
        await init_beanie(database=database,document_models=all_models)
        logger.info("Beanie inicializado con base de datos: %s",settings.MONGODB_DB_NAME)
    except Exception:
        logger.exception("Error inicializando Beanie")
        raise

def get_mongodb_client(request: Request) -> AsyncMongoClient:
    return request.app.state.mongodb_client