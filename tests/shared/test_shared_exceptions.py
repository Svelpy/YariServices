import pytest

from app.shared.errors.exceptions import AppException


class TestAppException:
    """Tests para AppException."""

    def test_mensaje_y_status_code_por_defecto(self):
        exc = AppException("algo salió mal")
        assert exc.message == "algo salió mal"
        assert exc.status_code == 400

    def test_status_code_personalizado_404(self):
        exc = AppException("no encontrado", status_code=404)
        assert exc.message == "no encontrado"
        assert exc.status_code == 404

    def test_status_code_personalizado_500(self):
        exc = AppException("error interno", status_code=500)
        assert exc.status_code == 500

    def test_is_operational_siempre_true(self):
        exc = AppException("test")
        assert exc.is_operational is True

    def test_es_subclase_de_exception(self):
        exc = AppException("test")
        assert isinstance(exc, Exception)

    def test_puede_capturarse_como_exception(self):
        with pytest.raises(Exception):
            raise AppException("capturada como Exception")

    def test_mensaje_accesible_via_args(self):
        exc = AppException("mensaje args")
        assert str(exc) == "mensaje args"
