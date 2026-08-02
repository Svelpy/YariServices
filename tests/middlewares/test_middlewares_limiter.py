"""
Tests para register_rate_limiter.

Verifica que el limiter se asigna al estado de la app y que el handler de
RateLimitExceeded queda registrado. No se realizan llamadas HTTP reales al
límite de rate.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from app.middlewares.limiter import limiter, register_rate_limiter


class TestRegisterRateLimiter:
    """Tests para register_rate_limiter."""

    def test_asigna_limiter_al_estado_de_la_app(self):
        app = FastAPI()
        register_rate_limiter(app)
        assert app.state.limiter is limiter

    def test_registra_handler_de_rate_limit_exceeded(self):
        app = FastAPI()
        app.add_exception_handler = MagicMock()

        register_rate_limiter(app)

        app.add_exception_handler.assert_called_once()
        args, _ = app.add_exception_handler.call_args
        assert args[0] is RateLimitExceeded

    def test_limiter_usa_get_remote_address(self):
        """El limiter debe usar get_remote_address como key_func."""
        from slowapi.util import get_remote_address
        assert limiter._key_func is get_remote_address

    def test_limiter_tiene_limite_por_defecto(self):
        """El limiter debe tener al menos un límite por defecto configurado."""
        assert limiter._default_limits is not None
        assert len(limiter._default_limits) > 0

    def test_multiple_registros_no_rompe_app(self):
        """Registrar dos veces no debe lanzar excepción."""
        app = FastAPI()
        register_rate_limiter(app)
        register_rate_limiter(app)
        assert app.state.limiter is limiter


class TestRegisterAllMiddlewares:
    """Tests para register_all_middlewares (orquestador del __init__.py)."""

    def test_llama_los_tres_registradores(self):
        from app.middlewares import register_all_middlewares

        app = FastAPI()

        with (
            patch("app.middlewares.register_rate_limiter") as mock_limiter,
            patch("app.middlewares.register_exception_handlers") as mock_exc,
            patch("app.middlewares.register_cors") as mock_cors,
        ):
            register_all_middlewares(app)

        mock_limiter.assert_called_once_with(app)
        mock_exc.assert_called_once_with(app)
        mock_cors.assert_called_once_with(app)

    def test_orden_de_registro(self):
        """rate_limiter debe registrarse antes que exception_handlers y cors."""
        from app.middlewares import register_all_middlewares

        app = FastAPI()
        call_order = []

        with (
            patch("app.middlewares.register_rate_limiter", side_effect=lambda a: call_order.append("limiter")),
            patch("app.middlewares.register_exception_handlers", side_effect=lambda a: call_order.append("exc")),
            patch("app.middlewares.register_cors", side_effect=lambda a: call_order.append("cors")),
        ):
            register_all_middlewares(app)

        assert call_order == ["limiter", "exc", "cors"]
