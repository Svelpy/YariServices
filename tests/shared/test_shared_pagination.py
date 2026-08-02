import pytest
from pydantic import BaseModel

from app.shared.schemas.pagination import PaginatedResponse


class ItemSchema(BaseModel):
    id: int
    name: str


class TestPaginatedResponse:
    """Tests para PaginatedResponse."""

    def test_instancia_con_datos_validos(self):
        response = PaginatedResponse[str](
            total=100,
            page=1,
            per_page=10,
            total_pages=10,
            data=["a", "b", "c"],
        )
        assert response.total == 100
        assert response.page == 1
        assert response.per_page == 10
        assert response.total_pages == 10
        assert response.data == ["a", "b", "c"]

    def test_tipado_generico_con_schema_pydantic(self):
        items = [ItemSchema(id=1, name="uno"), ItemSchema(id=2, name="dos")]
        response = PaginatedResponse[ItemSchema](
            total=2,
            page=1,
            per_page=10,
            total_pages=1,
            data=items,
        )
        assert len(response.data) == 2
        assert response.data[0].name == "uno"

    def test_data_lista_vacia(self):
        response = PaginatedResponse[str](
            total=0,
            page=1,
            per_page=10,
            total_pages=0,
            data=[],
        )
        assert response.data == []
        assert response.total == 0

    def test_primera_pagina(self):
        response = PaginatedResponse[int](
            total=50,
            page=1,
            per_page=25,
            total_pages=2,
            data=list(range(25)),
        )
        assert response.page == 1
        assert len(response.data) == 25

    def test_falla_sin_campo_total(self):
        with pytest.raises(Exception):
            PaginatedResponse[str](
                page=1,
                per_page=10,
                total_pages=1,
                data=["x"],
            )

    def test_falla_sin_campo_data(self):
        with pytest.raises(Exception):
            PaginatedResponse[str](
                total=5,
                page=1,
                per_page=10,
                total_pages=1,
            )
