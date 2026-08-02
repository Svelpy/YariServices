from fastapi import APIRouter, Response, status
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core import database as db_module

router = APIRouter()

@router.get("/", include_in_schema=False)
async def root():
    """Redirige automáticamente a la documentación interactiva en desarrollo"""
    if settings.DEBUG:
        return RedirectResponse(url="/docs")
    return {"message": "Svelpy API", "status": "active"}


@router.get("/health", tags=["Health"])
async def health_check(response: Response):
    """
    Endpoint de salud operativa (Readiness Probe).
    Verifica que la base de datos responda antes de retornar 200.
    """
    health_status = {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "disconnected"
    }
    
    try:
        # Pinguemos a la base de datos para verificar conexión real
        if db_module.mongodb_client is not None:
            await db_module.mongodb_client.admin.command('ping')
            health_status["database"] = "connected"
            return health_status
        else:
            raise Exception("Cliente de base de datos no inicializado")
            
    except Exception as e:
            response.status_code = 503
            return {
                "status": "error",
                "message": "Servicio no disponible temporalmente.",
                "details": {
                    "app": settings.APP_NAME,
                    "version": settings.APP_VERSION,
                    "database": "disconnected",
                    "reason": str(e)
                }
            }