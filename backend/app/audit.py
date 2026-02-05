from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AuditConfig


class AuditLogger:
    def __init__(self, data_dir: Path, config: AuditConfig) -> None:
        self.log_path = data_dir / "audit_log.jsonl"
        self.config = config
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._compiled = [re.compile(pattern) for pattern in config.redact_patterns]

    def log(self, payload: dict[str, Any]) -> None:
        payload["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
        redacted = self._redact(payload)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(redacted) + "\n")

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._redact(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, str):
            redacted = value
            for pattern in self._compiled:
                redacted = pattern.sub("<redacted>", redacted)
            return redacted
        return value
