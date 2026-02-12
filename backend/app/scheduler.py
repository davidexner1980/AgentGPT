from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from .dreams import Dreamer, Reflector, read_jsonl_tail


class SchedulerState:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "scheduler_state.json"

    def load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, payload: dict[str, str]) -> None:
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


async def run_scheduler(app) -> None:
    data_dir = app.state.data_dir
    state_store = SchedulerState(data_dir)
    dreamer = app.state.dreamer
    reflector = app.state.reflector
    while True:
        config = app.state.config_store.load()
        state = state_store.load()
        now = datetime.now(tz=timezone.utc)
        if config.dreams.enabled and now.hour >= config.dreams.daily_hour:
            last = state.get("last_dream_date")
            today = now.date().isoformat()
            if last != today:
                try:
                    await dreamer.run(config)
                    state["last_dream_date"] = today
                    state_store.save(state)
                except Exception:
                    pass
        if config.reflections.enabled and now.weekday() == config.reflections.weekly_day:
            last = state.get("last_reflection_week")
            current_week = f"{now.year}-W{now.isocalendar().week}"
            if last != current_week:
                audit = read_jsonl_tail(data_dir / "audit_log.jsonl", config.reflections.max_actions)
                dreams = read_jsonl_tail(data_dir / "dream_journal.jsonl", config.reflections.max_dreams)
                try:
                    await reflector.run(config, audit, dreams)
                    state["last_reflection_week"] = current_week
                    state_store.save(state)
                except Exception:
                    pass
        await asyncio.sleep(1800)
