from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "RoleVerse",
        "version": "0.1.0",
        "environment": "development",
    }


def test_client_root_is_available() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "RoleVerse" in response.text
