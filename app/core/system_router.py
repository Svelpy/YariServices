from fastapi import APIRouter, Response, status, Depends, Request
from fastapi.responses import RedirectResponse

from app.core.config import Settings, get_settings




router = APIRouter()

@router.get("/", include_in_schema=False)
async def root(settings: Settings = Depends(get_settings),):
    """Redirige automáticamente a la documentación interactiva en desarrollo"""
    if settings.DEBUG:
        return RedirectResponse(url="/docs")
    return {"message": "Svelpy API", "status": "active"}


@router.get("/health", tags=["Health"],)
async def health_check(request: Request,response: Response,settings: Settings = Depends(get_settings),):
    """
    Endpoint de salud operativa (Readiness Probe).
    Verifica que la base de datos responda antes de retornar 200.
    """
    
    try:
        database=request.app.state.database
        if database is None:
            raise RuntimeError("Base de datos no inicializada")
        
        await database.command('ping')
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": "connected"
        }
            
    except Exception as error:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {
                "status": "error",
                "message": "Servicio no disponible temporalmente.",
                "details": {
                    "app": settings.APP_NAME,
                    "version": settings.APP_VERSION,
                    "database": "disconnected",
                    "reason": str(error),
                },
            }