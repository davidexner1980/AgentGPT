from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config_store import ConfigStore
from .models import AppConfig
from .ollama import OllamaClient


class Dreamer:
    def __init__(self, data_dir: Path, ollama: OllamaClient, config_store: ConfigStore) -> None:
        self.log_path = data_dir / "dream_journal.jsonl"
        self.ollama = ollama
        self.config_store = config_store
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def run(self, config: AppConfig) -> dict[str, Any]:
        model = config.dreams.model or config.routing.default_model
        if not model:
            raise RuntimeError("No dream model configured")
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": config.prompts.dream},
                {"role": "user", "content": "Dream now."},
            ],
            "stream": False,
        }
        response = await self.ollama.chat(payload)
        content = response.get("message", {}).get("content", "")
        entry = {"timestamp": _now(), "model": model, "content": content}
        self._append(entry, self.log_path)
        return entry


class Reflector:
    def __init__(self, data_dir: Path, ollama: OllamaClient, config_store: ConfigStore) -> None:
        self.data_dir = data_dir
        self.log_path = data_dir / "reflection_journal.jsonl"
        self.ollama = ollama
        self.config_store = config_store
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def run(self, config: AppConfig, audit_tail: list[dict[str, Any]], dream_tail: list[dict[str, Any]]) -> dict[str, Any]:
        model = config.reflections.model or config.routing.default_model
        if not model:
            raise RuntimeError("No reflection model configured")
        prompt = {
            "dreams": dream_tail,
            "audits": audit_tail,
            "current_config": config.model_dump(mode="json"),
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": config.prompts.reflection},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            "stream": False,
        }
        response = await self.ollama.chat(payload)
        content = response.get("message", {}).get("content", "")
        proposal = _safe_json(content)
        entry = {"timestamp": _now(), "model": model, "proposal": proposal or content}
        if isinstance(proposal, dict):
            updated = _apply_proposal(config, proposal)
            if updated != config:
                self.config_store.save_with_diff(config, updated, reason="reflection_update")
                entry["applied"] = True
            else:
                entry["applied"] = False
        self._append(entry, self.log_path)
        return entry


def _apply_proposal(config: AppConfig, proposal: dict[str, Any]) -> AppConfig:
    payload = config.model_dump(mode="json")
    for key in ("routing", "permissions", "rag", "voice", "prompts"):
        if key in proposal:
            payload[key] = proposal[key]
    return AppConfig.model_validate(payload)


def _safe_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def read_jsonl_tail(path: Path, tail: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if tail:
        lines = lines[-tail:]
    return [json.loads(line) for line in lines if line.strip()]
