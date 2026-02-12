from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import inspect

from .audit import AuditLogger
from .models import ToolResult
from .policies import PolicyEngine
from .rag import RagIndex


@dataclass
class SkillManifest:
    name: str
    description: str
    required_permissions: list[str]
    tools: list[str]
    entrypoint: str


class SkillContext:
    def __init__(self, policy: PolicyEngine, audit: AuditLogger, rag: RagIndex) -> None:
        self.policy = policy
        self.audit = audit
        self.rag = rag

    def read_file(self, path: str) -> ToolResult:
        decision = self.policy.check_file_read(path)
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason, metadata={"approval": decision.model_dump()})
        content = Path(path).read_text(encoding="utf-8", errors="ignore")
        self.audit.log(
            {"tool": "file_read", "path": path, "decision": "allowed", "summary": "Read file"}
        )
        return ToolResult(success=True, output=content)

    def write_file(self, path: str, content: str) -> ToolResult:
        decision = self.policy.check_file_write(path)
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason, metadata={"approval": decision.model_dump()})
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path = target.with_suffix(target.suffix + ".bak")
        if target.exists():
            backup_path.write_text(target.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
        temp_path = target.with_suffix(target.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(target)
        self.audit.log(
            {"tool": "file_write", "path": path, "decision": "allowed", "summary": "Wrote file"}
        )
        return ToolResult(success=True, output="File written")

    def run_command(self, command: list[str]) -> ToolResult:
        joined = " ".join(command)
        decision = self.policy.check_terminal(joined)
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason, metadata={"approval": decision.model_dump()})
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            output = (result.stdout or "") + (result.stderr or "")
            self.audit.log(
                {"tool": "terminal", "command": joined, "decision": "allowed", "summary": "Ran command"}
            )
            return ToolResult(success=result.returncode == 0, output=output)
        except OSError as exc:
            return ToolResult(success=False, error=str(exc))

    async def rag_ingest(self, paths: list[str]) -> ToolResult:
        result = await self.rag.ingest_paths(paths)
        self.audit.log({"tool": "rag_ingest", "paths": paths, "decision": "allowed"})
        return ToolResult(success=True, metadata=result)


class SkillManager:
    def __init__(self, skills_dir: Path, context_factory: Callable[[], SkillContext]) -> None:
        self.skills_dir = skills_dir
        self.context_factory = context_factory
        self._manifests: dict[str, SkillManifest] = {}
        self._load_manifests()

    def _load_manifests(self) -> None:
        if not self.skills_dir.exists():
            return
        for manifest_path in self.skills_dir.glob("*/manifest.json"):
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = SkillManifest(
                name=data["name"],
                description=data.get("description", ""),
                required_permissions=data.get("required_permissions", []),
                tools=data.get("tools", []),
                entrypoint=data.get("entrypoint", "skill.py"),
            )
            self._manifests[manifest.name] = manifest

    def list_skills(self) -> list[SkillManifest]:
        return list(self._manifests.values())

    async def run(self, skill_name: str, payload: dict[str, Any]) -> ToolResult:
        manifest = self._manifests.get(skill_name)
        if not manifest:
            return ToolResult(success=False, error="Skill not found")
        skill_path = self.skills_dir / skill_name / manifest.entrypoint
        if not skill_path.exists():
            return ToolResult(success=False, error="Skill entrypoint missing")
        context = self.context_factory()
        namespace: dict[str, Any] = {}
        exec(skill_path.read_text(encoding="utf-8"), namespace)
        handler = namespace.get("run")
        if not callable(handler):
            return ToolResult(success=False, error="Skill missing run()")
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(context, payload)
            else:
                result = handler(context, payload)
            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=json.dumps(result))
        except Exception as exc:  # pragma: no cover - defensive
            return ToolResult(success=False, error=str(exc))
