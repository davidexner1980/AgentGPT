from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AppConfig, RouterRule


DEFAULT_ROUTER_RULES = [
    RouterRule(
        name="voice_fast",
        task_type="voice",
        min_quality=0,
        max_quality=60,
        model="llama3",
        fallback_model=None,
    ),
    RouterRule(
        name="coding_quality",
        task_type="coding",
        min_quality=61,
        max_quality=100,
        model="codellama",
        fallback_model="llama3",
    ),
    RouterRule(
        name="qa_fast",
        task_type="qa",
        min_quality=0,
        max_quality=60,
        model="llama3",
        fallback_model=None,
    ),
    RouterRule(
        name="reasoning_quality",
        task_type="reasoning",
        min_quality=61,
        max_quality=100,
        model="llama3",
        fallback_model=None,
    ),
    RouterRule(
        name="fallback_any",
        task_type="any",
        min_quality=0,
        max_quality=100,
        model="llama3",
        fallback_model=None,
    ),
]


class ConfigStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.config_path = data_dir / "config.json"
        self.diff_dir = data_dir / "config_diffs"
        self.diff_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            config = AppConfig()
            config.routing.rules = DEFAULT_ROUTER_RULES
            self.save(config)
            return config
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        return AppConfig.model_validate(raw)

    def save(self, config: AppConfig) -> None:
        payload = config.model_dump(mode="json")
        temp_path = self.config_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(self.config_path)

    def save_with_diff(self, before: AppConfig, after: AppConfig, reason: str) -> Path:
        diff_payload: dict[str, Any] = {
            "reason": reason,
            "before": before.model_dump(mode="json"),
            "after": after.model_dump(mode="json"),
        }
        diff_path = self.diff_dir / f"diff_{self._next_diff_id()}.json"
        diff_path.write_text(json.dumps(diff_payload, indent=2), encoding="utf-8")
        self.save(after)
        return diff_path

    def _next_diff_id(self) -> str:
        existing = sorted(self.diff_dir.glob("diff_*.json"))
        if not existing:
            return "0001"
        last = existing[-1].stem.split("_")[-1]
        try:
            return f"{int(last) + 1:04d}"
        except ValueError:
            return "0001"
