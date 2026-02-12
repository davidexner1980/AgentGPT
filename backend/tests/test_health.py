from fastapi.testclient import TestClient


def test_health(test_app):
    client = TestClient(test_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
