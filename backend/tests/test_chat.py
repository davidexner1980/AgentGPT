from fastapi.testclient import TestClient


def test_chat_basic(test_app):
    client = TestClient(test_app)
    response = client.post(
        "/chat",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "ok"
