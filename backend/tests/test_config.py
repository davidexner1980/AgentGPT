from fastapi.testclient import TestClient


def test_config_roundtrip(test_app):
    client = TestClient(test_app)
    response = client.get("/config")
    assert response.status_code == 200
    payload = response.json()
    payload["permissions"]["tools_enabled"] = True
    response = client.post("/config", json=payload)
    assert response.status_code == 200
    assert response.json()["permissions"]["tools_enabled"] is True
