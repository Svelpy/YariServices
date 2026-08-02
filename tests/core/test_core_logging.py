import logging
from unittest.mock import patch

import pytest

from app.core.logging import get_logger, setup_logging


class TestGetLogger:
    """Tests para get_logger."""

    def test_devuelve_instancia_de_logger(self):
        logger = get_logger("test_modulo")
        assert isinstance(logger, logging.Logger)

    def test_nombre_del_logger_correcto(self):
        logger = get_logger("mi_modulo")
        assert logger.name == "mi_modulo"

    def test_mismo_nombre_devuelve_mismo_logger(self):
        """Python garantiza singleton de loggers por nombre."""
        logger1 = get_logger("modulo_x")
        logger2 = get_logger("modulo_x")
        assert logger1 is logger2

    def test_distintos_nombres_distintos_loggers(self):
        logger_a = get_logger("modulo_a")
        logger_b = get_logger("modulo_b")
        assert logger_a is not logger_b
        assert logger_a.name != logger_b.name


class TestSetupLogging:
    """Tests para setup_logging.

    basicConfig() es idempotente en Python: si el root logger ya tiene handlers
    (pytest los añade antes de los tests), no reconfigura el nivel.
    Por eso parcheamos basicConfig y verificamos cómo se llama.
    """

    def test_debug_true_llama_basicconfig_con_nivel_debug(self):
        with (
            patch("app.core.logging.settings") as mock_settings,
            patch("app.core.logging.logging.basicConfig") as mock_basic,
        ):
            mock_settings.DEBUG = True
            setup_logging()
            mock_basic.assert_called_once()
            kwargs = mock_basic.call_args.kwargs
            assert kwargs["level"] == logging.DEBUG

    def test_debug_false_llama_basicconfig_con_nivel_warning(self):
        with (
            patch("app.core.logging.settings") as mock_settings,
            patch("app.core.logging.logging.basicConfig") as mock_basic,
        ):
            mock_settings.DEBUG = False
            setup_logging()
            mock_basic.assert_called_once()
            kwargs = mock_basic.call_args.kwargs
            assert kwargs["level"] == logging.WARNING

    def test_pymongo_siempre_en_warning(self):
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.DEBUG = True
            setup_logging()
            assert logging.getLogger("pymongo").level == logging.WARNING

    def test_motor_siempre_en_warning(self):
        with patch("app.core.logging.settings") as mock_settings:
            mock_settings.DEBUG = True
            setup_logging()
            assert logging.getLogger("motor").level == logging.WARNING
