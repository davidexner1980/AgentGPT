from fastapi.testclient import TestClient


def test_models(test_app):
    client = TestClient(test_app)
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert data["models"][0]["name"] == "llama3"
