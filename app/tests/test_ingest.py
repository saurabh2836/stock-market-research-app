"""
tests/test_ingest.py
---------------------
Unit tests for ingest routes using FastAPI TestClient.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.app_factory import create_app
from app.models.schemas import IngestPDFResult, IngestTableResult

client = TestClient(create_app())

DUMMY_PDF_BYTES = b"%PDF-1.4 dummy"

PDF_RESULT   = IngestPDFResult(source="2024.pdf", year=2024, visual_pages=2, text_chunks=10, errors=0)
TABLE_RESULT = IngestTableResult(source="2024.pdf", year=2024, tables_ingested=3, errors=0)


@patch("app.api.routes.ingest.ingest_pdf", return_value=PDF_RESULT)
@patch("app.api.routes.ingest.ingest_tables", return_value=TABLE_RESULT)
def test_ingest_pdf(mock_tables, mock_pdf):
    response = client.post(
        "/ingest/pdf",
        files={"file": ("2024.pdf", DUMMY_PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["year"] == 2024


@patch("app.api.routes.ingest.ingest_tables", return_value=TABLE_RESULT)
def test_ingest_tables(mock_tables):
    response = client.post(
        "/ingest/tables",
        files={"file": ("2024.pdf", DUMMY_PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["tables_ingested"] == 3


@patch("app.api.routes.ingest.ingest_pdf", return_value=PDF_RESULT)
@patch("app.api.routes.ingest.ingest_tables", return_value=TABLE_RESULT)
def test_ingest_all(mock_tables, mock_pdf):
    response = client.post(
        "/ingest/all",
        files={"file": ("2024.pdf", DUMMY_PDF_BYTES, "application/pdf")},
    )
    assert response.status_code == 200
    assert "pdf" in response.json() and "tables" in response.json()