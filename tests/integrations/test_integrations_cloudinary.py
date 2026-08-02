"""
Tests para CloudinaryService.

Toda la I/O real (cloudinary.uploader.upload / destroy) se mockea.
No se realizan llamadas a la API de Cloudinary en ningún test.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.cloudinary import CloudinaryService
from app.shared.errors.exceptions import AppException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload_file(
    content: bytes = b"fake-image-data",
    content_type: str = "image/jpeg",
    filename: str = "photo.jpg",
) -> MagicMock:
    """Crea un UploadFile falso (MagicMock) con los parámetros dados."""
    file = MagicMock()
    file.content_type = content_type
    file.filename = filename
    file.read = AsyncMock(return_value=content)
    file.seek = AsyncMock()
    return file


# ---------------------------------------------------------------------------
# _extract_public_id
# ---------------------------------------------------------------------------

class TestExtractPublicId:
    """Tests para CloudinaryService._extract_public_id."""

    def test_url_con_version_extrae_public_id(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1234567890/FOLDER/avatar.jpg"
        result = CloudinaryService._extract_public_id(url)
        assert result == "FOLDER/avatar"

    def test_url_sin_version_extrae_public_id(self):
        url = "https://res.cloudinary.com/demo/image/upload/FOLDER/avatar.jpg"
        result = CloudinaryService._extract_public_id(url)
        assert result == "FOLDER/avatar"

    def test_url_con_extension_png(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1/FOLDER/img.png"
        result = CloudinaryService._extract_public_id(url)
        assert result == "FOLDER/img"

    def test_url_con_carpeta_anidada(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1/YARI/users/profile.jpg"
        result = CloudinaryService._extract_public_id(url)
        assert result == "YARI/users/profile"

    def test_url_sin_upload_lanza_app_exception(self):
        with pytest.raises(AppException):
            CloudinaryService._extract_public_id("https://example.com/imagen.jpg")

    def test_url_vacia_lanza_app_exception(self):
        with pytest.raises(AppException):
            CloudinaryService._extract_public_id("")


# ---------------------------------------------------------------------------
# upload_image
# ---------------------------------------------------------------------------

class TestUploadImage:
    """Tests para CloudinaryService.upload_image (cloudinary.uploader.upload mockeado)."""

    @pytest.mark.asyncio
    async def test_sube_imagen_valida_retorna_url(self):
        file = _make_upload_file(content_type="image/jpeg")
        fake_url = "https://res.cloudinary.com/demo/image/upload/v1/YARI/test/photo.jpg"

        with patch("app.integrations.cloudinary.cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {"secure_url": fake_url}
            result = await CloudinaryService.upload_image(file, folder="test")

        assert result == fake_url

    @pytest.mark.asyncio
    async def test_sube_imagen_png_valida(self):
        file = _make_upload_file(content_type="image/png", filename="foto.png")
        fake_url = "https://res.cloudinary.com/demo/image/upload/foto.png"

        with patch("app.integrations.cloudinary.cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {"secure_url": fake_url}
            result = await CloudinaryService.upload_image(file, folder="products")

        assert result == fake_url

    @pytest.mark.asyncio
    async def test_archivo_no_imagen_lanza_app_exception(self):
        file = _make_upload_file(content_type="application/pdf", filename="doc.pdf")

        with pytest.raises(AppException) as exc_info:
            await CloudinaryService.upload_image(file, folder="test")

        assert exc_info.value.status_code == 400
        assert "imagen" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_svg_bloqueado_por_content_type(self):
        file = _make_upload_file(content_type="image/svg+xml", filename="icon.svg")

        with pytest.raises(AppException) as exc_info:
            await CloudinaryService.upload_image(file, folder="test")

        assert exc_info.value.status_code == 400
        assert "SVG" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_svg_bloqueado_por_extension(self):
        file = _make_upload_file(content_type="image/jpeg", filename="malicious.svg")

        with pytest.raises(AppException) as exc_info:
            await CloudinaryService.upload_image(file, folder="test")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_imagen_mayor_5mb_lanza_app_exception(self):
        contenido_grande = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
        file = _make_upload_file(content=contenido_grande, content_type="image/jpeg")

        with pytest.raises(AppException) as exc_info:
            await CloudinaryService.upload_image(file, folder="test")

        assert exc_info.value.status_code == 400
        assert "5MB" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_imagen_exactamente_5mb_es_valida(self):
        contenido_5mb = b"x" * (5 * 1024 * 1024)
        file = _make_upload_file(content=contenido_5mb, content_type="image/jpeg")

        with patch("app.integrations.cloudinary.cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test.jpg"}
            result = await CloudinaryService.upload_image(file, folder="test")

        assert result is not None

    @pytest.mark.asyncio
    async def test_llama_seek_al_finalizar(self):
        """Verifica que seek(0) siempre se llama (bloque finally)."""
        file = _make_upload_file(content_type="image/jpeg")

        with patch("app.integrations.cloudinary.cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test.jpg"}
            await CloudinaryService.upload_image(file, folder="test")

        file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_llama_seek_aunque_falle_upload(self):
        """seek(0) debe llamarse incluso si cloudinary.upload falla."""
        file = _make_upload_file(content_type="image/jpeg")

        with patch(
            "app.integrations.cloudinary.cloudinary.uploader.upload",
            side_effect=Exception("Cloudinary error"),
        ):
            with pytest.raises(Exception, match="Cloudinary error"):
                await CloudinaryService.upload_image(file, folder="test")

        file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_upload_usa_carpeta_correcta(self):
        """Verifica que upload recibe la carpeta combinada settings.FOLDER/folder."""
        file = _make_upload_file(content_type="image/jpeg")

        with (
            patch("app.integrations.cloudinary.cloudinary.uploader.upload") as mock_upload,
            patch("app.integrations.cloudinary.settings") as mock_settings,
        ):
            mock_settings.CLOUDINARY_FOLDER_NAME = "YARI"
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test.jpg"}
            await CloudinaryService.upload_image(file, folder="avatars")

        call_kwargs = mock_upload.call_args.kwargs
        assert call_kwargs["folder"] == "YARI/avatars"

    @pytest.mark.asyncio
    async def test_upload_resource_type_es_image(self):
        file = _make_upload_file(content_type="image/jpeg")

        with patch("app.integrations.cloudinary.cloudinary.uploader.upload") as mock_upload:
            mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test.jpg"}
            await CloudinaryService.upload_image(file, folder="test")

        call_kwargs = mock_upload.call_args.kwargs
        assert call_kwargs["resource_type"] == "image"


# ---------------------------------------------------------------------------
# delete_image
# ---------------------------------------------------------------------------

class TestDeleteImage:
    """Tests para CloudinaryService.delete_image (cloudinary.uploader.destroy mockeado)."""

    @pytest.mark.asyncio
    async def test_elimina_imagen_valida_retorna_true(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1/YARI/avatar.jpg"

        with patch("app.integrations.cloudinary.cloudinary.uploader.destroy") as mock_destroy:
            mock_destroy.return_value = {"result": "ok"}
            result = await CloudinaryService.delete_image(url)

        assert result is True

    @pytest.mark.asyncio
    async def test_elimina_imagen_falla_retorna_false(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1/YARI/avatar.jpg"

        with patch("app.integrations.cloudinary.cloudinary.uploader.destroy") as mock_destroy:
            mock_destroy.return_value = {"result": "not found"}
            result = await CloudinaryService.delete_image(url)

        assert result is False

    @pytest.mark.asyncio
    async def test_url_vacia_retorna_false_sin_llamar_destroy(self):
        with patch("app.integrations.cloudinary.cloudinary.uploader.destroy") as mock_destroy:
            result = await CloudinaryService.delete_image("")

        assert result is False
        mock_destroy.assert_not_called()

    @pytest.mark.asyncio
    async def test_url_none_retorna_false(self):
        with patch("app.integrations.cloudinary.cloudinary.uploader.destroy") as mock_destroy:
            result = await CloudinaryService.delete_image(None)

        assert result is False
        mock_destroy.assert_not_called()

    @pytest.mark.asyncio
    async def test_destroy_recibe_public_id_correcto(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1/YARI/users/avatar.jpg"

        with patch("app.integrations.cloudinary.cloudinary.uploader.destroy") as mock_destroy:
            mock_destroy.return_value = {"result": "ok"}
            await CloudinaryService.delete_image(url)

        mock_destroy.assert_called_once_with("YARI/users/avatar")
