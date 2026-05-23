"""
tests/test_query_ask_plot.py
-----------------------------
Unit tests for /query, /ask, and /plot routes.
"""
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.app_factory import create_app
from app.models.schemas import QueryHit

client = TestClient(create_app())

SAMPLE_HITS = [
    QueryHit(score=0.95, page=5, type="text", text="Revenue grew 20%.", source="2024.pdf", year=2024),
    QueryHit(score=0.88, page=12, type="table", text="EBITDA table.", source="2023.pdf", year=2023,
             headers='["Year","EBITDA"]', records='[{"Year":"2023","EBITDA":"500"}]'),
]


@patch("app.api.routes.query.run_query", return_value=SAMPLE_HITS)
def test_query(mock_query):
    response = client.post("/query/", json={"question": "revenue growth", "top_k": 5})
    assert response.status_code == 200
    assert len(response.json()["hits"]) == 2


@patch("app.api.routes.ask.run_ask", return_value="Revenue grew by 20% in FY2024.")
def test_ask(mock_ask):
    response = client.post("/ask/", json={"question": "What was revenue growth?"})
    assert response.status_code == 200
    assert "answer" in response.json()


@patch("app.api.routes.plot.generate_plot", return_value=Path("/tmp/chart_all.png"))
def test_plot(mock_plot):
    dummy = Path("/tmp/chart_all.png")
    dummy.write_bytes(b"\x89PNG\r\n\x1a\n")
    response = client.post("/plot/", json={"question": "EBITDA trend"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"