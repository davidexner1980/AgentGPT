from __future__ import annotations

from pathlib import Path
from typing import Any, AsyncIterator

import pytest

from app.main import create_app
from app.ollama import OllamaClient


class FakeOllama(OllamaClient):
    def __init__(self) -> None:
        super().__init__("http://127.0.0.1:11434")

    async def list_models(self) -> list[dict[str, Any]]:
        return [{"name": "llama3"}]

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"message": {"content": "ok"}}

    async def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        yield {"message": {"content": "ok"}, "done": True}

    async def embed(self, model: str, inputs: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in inputs]


@pytest.fixture()
def test_app(tmp_path: Path):
    app = create_app(data_dir=tmp_path, ollama_client=FakeOllama())
    return app
