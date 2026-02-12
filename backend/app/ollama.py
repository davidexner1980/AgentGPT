from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx


class OllamaClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags", timeout=15)
            response.raise_for_status()
            payload = response.json()
            return payload.get("models", [])

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload, timeout=60)
            response.raise_for_status()
            return response.json()

    async def stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        payload = {**payload, "stream": True}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=None,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    async def embed(self, model: str, inputs: list[str]) -> list[list[float]]:
        payload = {"model": model, "input": inputs}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}/api/embed", json=payload, timeout=60)
            if response.status_code == 404:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": inputs[0]},
                    timeout=60,
                )
            response.raise_for_status()
            data = response.json()
            if "embeddings" in data:
                return data["embeddings"]
            if "embedding" in data:
                return [data["embedding"]]
            raise ValueError("Unexpected embedding payload")

    async def ping_model(self, model: str) -> float:
        payload = {"model": model, "messages": [{"role": "user", "content": "ping"}], "stream": False}
        start = time.perf_counter()
        await self.chat(payload)
        return time.perf_counter() - start
