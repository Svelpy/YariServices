from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.logging import setup_logging
from app.middlewares import register_all_middlewares
from app.api import api_router

# Inicializar logging
setup_logging()

#Ciclo de vida
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de ciclo de vida: startup y shutdown."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


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
register_all_middlewares(app)

# Registrar routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
