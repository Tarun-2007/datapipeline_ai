"""
DataPulse AI - Integration Tests for FastAPI REST Endpoints
"""
import pytest


def test_health_check_endpoint(api_client):
    """Verifies GET /health returns platform health."""
    resp = api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "database_connected" in data


def test_sales_summary_endpoint(api_client):
    """Verifies GET /api/v1/sales/summary returns headline KPIs."""
    resp = api_client.get("/api/v1/sales/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert "total_transactions" in data
    assert "average_order_value" in data


def test_data_quality_summary_endpoint(api_client):
    """Verifies GET /api/v1/data-quality/summary returns audit metrics."""
    resp = api_client.get("/api/v1/data-quality/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_records_ingested" in data
    assert "valid_records_stored" in data


def test_mock_sales_api_pagination(api_client):
    """Verifies GET /api/v1/mock-api/sales pagination logic."""
    resp = api_client.get("/api/v1/mock-api/sales?page=1&page_size=25")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 25
    assert len(data["data"]) == 25
    assert "transaction_id" in data["data"][0]
