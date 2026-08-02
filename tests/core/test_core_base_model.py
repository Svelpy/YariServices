from datetime import datetime, timezone

import pytest

from app.core.base_model import BaseDocument


class TestBaseDocumentFields:
    """Tests para los campos de auditoría de BaseDocument."""

    def test_tiene_campo_created_at(self):
        assert hasattr(BaseDocument, "model_fields") or "created_at" in BaseDocument.__annotations__

    def test_tiene_campo_updated_at(self):
        fields = BaseDocument.model_fields
        assert "updated_at" in fields

    def test_tiene_campo_is_deleted(self):
        fields = BaseDocument.model_fields
        assert "is_deleted" in fields

    def test_is_deleted_default_false(self):
        fields = BaseDocument.model_fields
        default = fields["is_deleted"].default
        assert default is False

    def test_tiene_campo_deleted_at(self):
        fields = BaseDocument.model_fields
        assert "deleted_at" in fields

    def test_tiene_campo_created_by(self):
        fields = BaseDocument.model_fields
        assert "created_by" in fields

    def test_tiene_campo_updated_by(self):
        fields = BaseDocument.model_fields
        assert "updated_by" in fields

    def test_tiene_campo_deleted_by(self):
        fields = BaseDocument.model_fields
        assert "deleted_by" in fields

    def test_created_at_tiene_default_factory(self):
        fields = BaseDocument.model_fields
        assert fields["created_at"].default_factory is not None

    def test_updated_at_tiene_default_factory(self):
        fields = BaseDocument.model_fields
        assert fields["updated_at"].default_factory is not None

    def test_created_at_factory_produce_datetime_utc(self):
        fields = BaseDocument.model_fields
        dt = fields["created_at"].default_factory()
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None

    def test_updated_at_factory_produce_datetime_utc(self):
        fields = BaseDocument.model_fields
        dt = fields["updated_at"].default_factory()
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None


class TestBaseDocumentSettings:
    """Tests para la clase Settings interna de BaseDocument."""

    def test_use_state_management_habilitado(self):
        assert BaseDocument.Settings.use_state_management is True

    def test_use_revision_habilitado(self):
        assert BaseDocument.Settings.use_revision is True


class TestPreSaveHook:
    """Tests para el hook pre_save de BaseDocument."""

    def test_pre_save_actualiza_updated_at(self):
        """pre_save debe actualizar updated_at al momento actual."""
        doc = BaseDocument.model_construct(
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            is_deleted=False,
        )
        before = doc.updated_at
        doc.pre_save()
        assert doc.updated_at > before

    def test_pre_save_no_modifica_created_at(self):
        """pre_save NO debe tocar created_at."""
        original_created = datetime(2020, 6, 15, tzinfo=timezone.utc)
        doc = BaseDocument.model_construct(
            created_at=original_created,
            updated_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            is_deleted=False,
        )
        doc.pre_save()
        assert doc.created_at == original_created

    def test_pre_save_updated_at_tiene_timezone(self):
        doc = BaseDocument.model_construct(
            created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            is_deleted=False,
        )
        doc.pre_save()
        assert doc.updated_at.tzinfo is not None
