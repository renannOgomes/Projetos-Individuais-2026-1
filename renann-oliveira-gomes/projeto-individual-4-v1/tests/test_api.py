"""Testes para API."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data
    assert "graphql" in data["endpoints"]


@pytest.mark.asyncio
async def test_graphql_query():
    """Test GraphQL query."""
    query = """
    {
      conjuntura(empresa: "MRV", ano: 2025, trimestre: 3) {
        empresa
        ano
        trimestre
      }
    }
    """
    
    response = client.post(
        "/graphql",
        json={"query": query}
    )
    assert response.status_code == 200
