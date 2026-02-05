from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import ApprovalDecision, PermissionConfig


@dataclass
class ApprovalRecord:
    scope: str
    expires_at: datetime | None


class ApprovalStore:
    def __init__(self) -> None:
        self._records: list[ApprovalRecord] = []

    def add(self, scope: str, expires_at: datetime | None) -> None:
        self._records.append(ApprovalRecord(scope=scope, expires_at=expires_at))

    def is_approved(self, scope: str) -> bool:
        now = datetime.now(tz=timezone.utc)
        for record in self._records:
            if record.scope != scope:
                continue
            if record.expires_at and record.expires_at < now:
                continue
            return True
        return False


class PolicyEngine:
    def __init__(self, config: PermissionConfig, approvals: ApprovalStore | None = None) -> None:
        self.config = config
        self.approvals = approvals or ApprovalStore()

    def check_file_read(self, path: str) -> ApprovalDecision:
        return self._check_path(path, self.config.file_read_allowlist, "file_read")

    def check_file_write(self, path: str) -> ApprovalDecision:
        return self._check_path(path, self.config.file_write_allowlist, "file_write")

    def check_terminal(self, command: str) -> ApprovalDecision:
        if not self.config.tools_enabled or not self.config.terminal_enabled:
            return ApprovalDecision(
                allowed=False,
                reason="Terminal access disabled",
                scope=f"terminal:{command}",
                requires_approval=True,
            )
        if command in self.config.terminal_allowlist:
            return ApprovalDecision(
                allowed=True,
                reason="Allowlisted command",
                scope=f"terminal:{command}",
                requires_approval=False,
            )
        scope = f"terminal:{command}"
        if self.approvals.is_approved(scope):
            return ApprovalDecision(
                allowed=True,
                reason="Approved command",
                scope=scope,
                requires_approval=False,
            )
        return ApprovalDecision(
            allowed=False,
            reason="Command not allowlisted",
            scope=scope,
            requires_approval=True,
        )

    def check_skill(self, skill_name: str) -> ApprovalDecision:
        if not self.config.tools_enabled:
            return ApprovalDecision(
                allowed=False,
                reason="Tools disabled",
                scope=f"skill:{skill_name}",
                requires_approval=True,
            )
        if skill_name in self.config.skills_enabled:
            return ApprovalDecision(
                allowed=True,
                reason="Skill enabled",
                scope=f"skill:{skill_name}",
                requires_approval=False,
            )
        scope = f"skill:{skill_name}"
        if self.approvals.is_approved(scope):
            return ApprovalDecision(
                allowed=True,
                reason="Skill approved",
                scope=scope,
                requires_approval=False,
            )
        return ApprovalDecision(
            allowed=False,
            reason="Skill not enabled",
            scope=scope,
            requires_approval=True,
        )

    def _check_path(self, path: str, allowlist: Iterable[str], scope_prefix: str) -> ApprovalDecision:
        if not self.config.tools_enabled:
            return ApprovalDecision(
                allowed=False,
                reason="Tools disabled",
                scope=f"{scope_prefix}:{path}",
                requires_approval=True,
            )
        resolved = Path(path).resolve()
        for entry in allowlist:
            if resolved.is_relative_to(Path(entry).resolve()):
                return ApprovalDecision(
                    allowed=True,
                    reason="Allowlisted path",
                    scope=f"{scope_prefix}:{path}",
                    requires_approval=False,
                )
        scope = f"{scope_prefix}:{path}"
        if self.approvals.is_approved(scope):
            return ApprovalDecision(
                allowed=True,
                reason="Approved path",
                scope=scope,
                requires_approval=False,
            )
        return ApprovalDecision(
            allowed=False,
            reason="Path not allowlisted",
            scope=scope,
            requires_approval=True,
        )
