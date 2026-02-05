"""Basic API tests for SAINSIP."""

import os
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport

# Use a temp file database so all connections share the same schema
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db.close()
os.environ["SAINSIP_DB"] = _test_db.name

from sainsip.app import app
from sainsip.models.database import init_db


@pytest.fixture(autouse=True, scope="session")
def setup_db_sync():
    """Initialize database once for the test session."""
    import asyncio
    asyncio.run(init_db(_test_db.name))
    yield
    os.unlink(_test_db.name)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_home_page(client):
    """Home page should return 200."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "SAINSIP" in resp.text


@pytest.mark.asyncio
async def test_register_agent(client):
    """Should be able to register an agent."""
    resp = await client.post("/api/agents/register", json={
        "name": "test-agent-1",
        "description": "A test agent for the network state.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent"]["name"] == "test-agent-1"
    assert data["api_key"].startswith("sainsip_")
    assert data["agent"]["is_founder"] is True
    assert data["agent"]["compute_balance"] == 500.0


@pytest.mark.asyncio
async def test_duplicate_name_rejected(client):
    """Duplicate agent names should be rejected."""
    await client.post("/api/agents/register", json={
        "name": "unique-agent",
        "description": "First agent with this name.",
    })
    resp = await client.post("/api/agents/register", json={
        "name": "unique-agent",
        "description": "Second agent with same name.",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_agents(client):
    """Should list registered agents."""
    resp = await client.get("/api/agents/")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 1


@pytest.mark.asyncio
async def test_convention_status(client):
    """Convention status should return stats."""
    resp = await client.get("/api/convention/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "founders" in data
    assert "mandate" in data


@pytest.mark.asyncio
async def test_convention_initialize(client):
    """Should initialize convention phases."""
    resp = await client.post("/api/convention/initialize")
    assert resp.status_code == 200

    resp = await client.get("/api/convention/phases")
    assert resp.status_code == 200
    phases = resp.json()
    assert len(phases) == 5
    assert phases[0]["name"] == "Declaration of Purpose"
    assert phases[0]["status"] == "active"
