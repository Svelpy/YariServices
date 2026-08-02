import traceback
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.shared.errors.exceptions import AppException
from app.domains.error_logs import ErrorLog

logger = logging.getLogger(__name__)

def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra los interceptores globales de errores en la app.
    """
    
    #Errores esperados
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "fail",
                "message": exc.message,
                "details": {}
            }
        )

    #Errores de validación de datos 
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors_details = {
            " -> ".join(str(x) for x in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0]): error["msg"]
            for error in exc.errors()
        }

        return JSONResponse(
            status_code=422,
            content={
                "status": "fail",
                "message": "Los datos enviados no son válidos.",
                "details": errors_details
            }
        )

    #Errores HTTP
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "fail",
                "message": exc.detail,
                "details": {}
            },
            headers=exc.headers
        )

    #Errores inesperados con codigo 500
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        stack_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

        if settings.DEBUG: 
            logger.error(f"Error crítico detectado: {exc}\n{stack_trace}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": str(exc),
                    "details": {
                        "stack":stack_trace
                    }    
                }
            )

        else:
            try:
                # Guardar en MongoDB ----------------------------------------------------
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
                user_id = None
                if hasattr(request.state, "user"):
                    user_id = str(request.state.user.id)
                
               
                log = ErrorLog(
                    status="error",
                    message=str(exc),
                    stack=stack_trace,
                    path=request.url.path,
                    method=request.method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    user_id=user_id
                )
                await log.insert()
                
            except Exception as db_err:
                logger.error(f"Error al intentar guardar log en MongoDB: {db_err}")
            # --------------------------- ----------------------------------------------------    
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "¡Miechi! Algo salió muy mal",
                    "details": {}
                }
            )
