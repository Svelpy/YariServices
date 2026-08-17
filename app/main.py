from contextlib import asynccontextmanager
from pymongo import AsyncMongoClient
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.database import initialize_beanie
from app.core.logging import setup_logging
from app.integrations.cloudinary import configure_cloudinary
from app.integrations.redis import create_redis_client
from app.integrations.resend import configure_resend
from app.middlewares import register_all_middlewares
from app.api import api_router

settings = get_settings()
setup_logging(settings)


#Ciclo de vida
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de ciclo de vida: startup y shutdown."""
    configure_cloudinary(settings)
    configure_resend(settings)
    redis_client = None
    mongodb_client = None
    try:
        redis_client = create_redis_client(settings)
        mongodb_client = AsyncMongoClient(settings.MONGODB_URL,tz_aware=True)
        database = mongodb_client.get_database(settings.MONGODB_DB_NAME)
        await database.command("ping")
        await redis_client.ping()
        await initialize_beanie(database, settings)
        app.state.mongodb_client = mongodb_client
        app.state.database = database
        app.state.redis_client = redis_client
        yield
    finally:
        if redis_client is not None:
            await redis_client.aclose()

        if mongodb_client is not None:
            await mongodb_client.close()


# Crear aplicación
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Registrar middlewares
register_all_middlewares(app,settings)

# Registrar routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
