"""Tests for GET /api/v1/situations endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_includes_situations_count():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["situations_loaded"] == 32


@pytest.mark.asyncio
async def test_list_situations_returns_all():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/situations/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 32
    ids = {s["id"] for s in data}
    assert {"shop", "marketplace", "bank", "employer", "insurance", "utility", "airline"} <= ids


@pytest.mark.asyncio
async def test_list_situations_fields():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/situations/")
    data = resp.json()
    for item in data:
        assert "id" in item
        assert "title" in item
        assert "blurb" in item
        assert "category" in item
        assert "document_type" in item
        # system_prompt and wizard_steps NOT exposed in list endpoint
        assert "system_prompt" not in item
        assert "wizard_steps" not in item


@pytest.mark.asyncio
async def test_get_situation_detail():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/situations/shop")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "shop"
    assert "wizard_steps" in data
    assert len(data["wizard_steps"]) >= 2
    assert "template_ready" in data
    assert data["template_ready"] is False  # no templates yet
    # system_prompt must NOT be exposed
    assert "system_prompt" not in data


@pytest.mark.asyncio
async def test_get_situation_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/situations/does_not_exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("situation_id", [
    "shop", "marketplace", "bank", "bank_block", "employer", "insurance",
    "utility", "airline", "court_order", "gibdd", "rental_deposit",
    "tour_operator", "online_course", "neighbor_flood", "repair", "telecom",
    "medical", "ddu_delay", "ddu_defects", "ddu_termination", "dtp_osago",
    "auto_repair", "debt_collector", "carsharing", "gym_refund",
    "education_refund", "gibdd_camera", "ip_employer", "mfo",
    "online_shop_delivery", "repair_apartment", "university_admission",
])
async def test_detail_has_contact_step(situation_id: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/situations/{situation_id}")
    assert resp.status_code == 200
    steps = resp.json()["wizard_steps"]
    last_step_fields = {f["id"] for f in steps[-1]["fields"]}
    assert "full_name" in last_step_fields
    assert "email" in last_step_fields
