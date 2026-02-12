from __future__ import annotations

from pathlib import Path


def run(context, payload):
    action = payload.get("action", "list")
    path = payload.get("path", ".")
    if action == "read":
        return context.read_file(path)
    if action == "list":
        resolved = Path(path).resolve()
        decision = context.policy.check_file_read(str(resolved))
        if not decision.allowed:
            return {
                "success": False,
                "error": decision.reason,
                "metadata": {"approval": decision.model_dump()},
            }
        entries = []
        for entry in resolved.iterdir():
            entries.append(
                {
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                }
            )
        return {"success": True, "output": entries}
    return {"success": False, "error": "Unsupported action"}
