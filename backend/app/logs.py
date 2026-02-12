from __future__ import annotations

import json
from pathlib import Path


def read_tail(path: Path, tail: int) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if tail:
        lines = lines[-tail:]
    return [json.loads(line) for line in lines if line.strip()]
