from __future__ import annotations


COMMANDS = {
    "git_status": ["git", "status", "-sb"],
    "pytest": ["pytest"],
    "ruff": ["ruff", "check", "."],
}


def run(context, payload):
    action = payload.get("action", "git_status")
    command = COMMANDS.get(action)
    if not command:
        return {"success": False, "error": "Unsupported action"}
    return context.run_command(command)
