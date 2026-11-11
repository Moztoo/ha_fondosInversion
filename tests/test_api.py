"""Integration tests for FastAPI endpoints."""
import os
import tempfile
import pytest
from starlette.testclient import TestClient

from app.config import settings
from app.database import init_db
from app.main import app
from app.service import FondosService

@pytest.fixture(scope="module")
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    settings.DATABASE_PATH = path
    init_db(path)

    # Ingest sample data if test PDF exists
    if os.path.exists("/tmp/bbva_00003776.pdf"):
        with open("/tmp/bbva_00003776.pdf", "rb") as f:
            pdf_bytes = f.read()
        service = FondosService(db_path=path)
        service.sync_data(custom_pdf_bytes=pdf_bytes)

    with TestClient(app) as tc:
        yield tc

    if os.path.exists(path):
        os.remove(path)

def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert "status" in json_data["data"]
    assert json_data["data"]["status"] == "healthy"

def test_filters_endpoint(client):
    res = client.get("/api/v1/filters")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert "segments" in json_data["data"]
    assert "categories" in json_data["data"]

def test_list_series_endpoint(client):
    res = client.get("/api/v1/series?limit=10")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert len(json_data["data"]) > 0
    sample = json_data["data"][0]
    assert "ticker" in sample
    assert "series" in sample
    assert "precio" in sample
    assert "rendimiento_1a" in sample
    assert "rendimiento_diario" in sample
    assert "minimo_inversion" in sample
    assert "category" in sample
    assert "segment" in sample

def test_list_funds_endpoint(client):
    res = client.get("/api/v1/funds?limit=10")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert "meta" in json_data

def test_not_found_fund_endpoint(client):
    res = client.get("/api/v1/funds/NONEXISTENT_TICKER_XYZ")
    assert res.status_code == 404
    json_data = res.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "FUND_NOT_FOUND"

def test_contract_endpoint(client):
    res = client.get("/api/v1/contract")
    assert res.status_code == 200
    openapi_spec = res.json()
    assert "openapi" in openapi_spec
    assert "paths" in openapi_spec

def test_favorite_flow_and_filtering(client):
    # 1. Fetch first series
    res = client.get("/api/v1/series?limit=1")
    assert res.status_code == 200
    series_list = res.json()["data"]
    assert len(series_list) > 0
    item = series_list[0]
    ticker = item["ticker"]
    series = item["series"]

    # 2. Toggle favorite ON
    toggle_res = client.post(f"/api/v1/favorites/{ticker}/{series}/toggle")
    assert toggle_res.status_code == 200
    data = toggle_res.json()["data"]
    assert data["is_favorite"] is True
    assert data["ticker"] == ticker

    # 3. Verify in favorites endpoint
    fav_res = client.get("/api/v1/favorites")
    assert fav_res.status_code == 200
    favs = fav_res.json()["data"]
    assert any(f["ticker"] == ticker and f["series"] == series for f in favs)

    # 4. Verify in series endpoint with only_favorites=true
    filter_res = client.get("/api/v1/series?only_favorites=true")
    assert filter_res.status_code == 200
    filtered = filter_res.json()["data"]
    assert all(f["is_favorite"] is True for f in filtered)
    assert any(f["ticker"] == ticker and f["series"] == series for f in filtered)

    # 5. Toggle favorite OFF
    toggle_off_res = client.post(f"/api/v1/favorites/{ticker}/{series}/toggle")
    assert toggle_off_res.status_code == 200
    assert toggle_off_res.json()["data"]["is_favorite"] is False
