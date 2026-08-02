from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

#creamos el limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

#registramos el limiter
def register_rate_limiter(app: FastAPI)-> None:
    """
    Registra el middleware de rate limiting en la app.
    Limita por defecto a 100 peticiones por minuto por IP.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)