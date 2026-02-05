from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RouterRule(BaseModel):
    name: str
    task_type: Literal["coding", "qa", "reasoning", "voice", "general", "any"]
    min_quality: int = 0
    max_quality: int = 100
    model: str
    fallback_model: str | None = None
    match_keywords: list[str] = Field(default_factory=list)
    max_context: int | None = None


class RoutingConfig(BaseModel):
    speed_quality: int = 50
    rules: list[RouterRule] = Field(default_factory=list)
    default_model: str | None = None


class PermissionConfig(BaseModel):
    tools_enabled: bool = False
    file_read_allowlist: list[str] = Field(default_factory=list)
    file_write_allowlist: list[str] = Field(default_factory=list)
    terminal_enabled: bool = False
    terminal_allowlist: list[str] = Field(default_factory=list)
    skills_enabled: list[str] = Field(default_factory=list)
    require_approval: bool = True


class RagConfig(BaseModel):
    enabled: bool = True
    embedding_model: str = "nomic-embed-text"
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4
    embedding_dim: int = 768


class VoiceConfig(BaseModel):
    enabled: bool = False
    hands_free: bool = False
    wake_word_enabled: bool = False
    piper_path: str | None = None
    piper_model: str | None = None


class DreamConfig(BaseModel):
    enabled: bool = True
    model: str | None = None
    daily_hour: int = 2
    max_entries: int = 30


class ReflectionConfig(BaseModel):
    enabled: bool = True
    model: str | None = None
    weekly_day: int = 6
    max_dreams: int = 14
    max_actions: int = 200


class AuditConfig(BaseModel):
    redact_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?i)api[_-]?key\s*[:=]\s*([A-Za-z0-9_-]{8,})",
            r"(?i)token\s*[:=]\s*([A-Za-z0-9._-]{8,})",
            r"(?i)password\s*[:=]\s*([^\s]+)",
        ]
    )
    retention_days: int = 30


class PromptConfig(BaseModel):
    system: str = (
        "You are a local-only personal AI assistant. Prioritize safety, auditability, "
        "and respond with concise, actionable guidance."
    )
    dream: str = (
        "Generate a hypothetical scenario about improving a local AI assistant. "
        "Do not call tools or refer to real user data. Write 3-5 bullet points."
    )
    reflection: str = (
        "Given recent dreams and tool audits, propose config-only improvements. "
        "Respond in JSON with optional routing or safety changes."
    )


class AppConfig(BaseModel):
    ollama_base_url: str = "http://127.0.0.1:11434"
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
    permissions: PermissionConfig = Field(default_factory=PermissionConfig)
    rag: RagConfig = Field(default_factory=RagConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    dreams: DreamConfig = Field(default_factory=DreamConfig)
    reflections: ReflectionConfig = Field(default_factory=ReflectionConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    prompts: PromptConfig = Field(default_factory=PromptConfig)


class ModelTag(BaseModel):
    name: str
    size: int | None = None
    modified_at: datetime | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatRequest(BaseModel):
    session_id: str | None = None
    messages: list[ChatMessage]
    model: str | None = None
    task_type: str | None = None
    speed_quality: int | None = None
    stream: bool = False
    use_rag: bool = True


class ChatResponse(BaseModel):
    model: str
    content: str
    routing_rule: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class RagIngestRequest(BaseModel):
    paths: list[str]


class RagSearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class RouterTestRequest(BaseModel):
    message: str
    task_type: str | None = None
    speed_quality: int | None = None
    model: str | None = None


class ApprovalRequest(BaseModel):
    scope: str
    expires_at: datetime | None = None


class ApprovalDecision(BaseModel):
    allowed: bool
    reason: str
    scope: str
    requires_approval: bool


class ToolResult(BaseModel):
    success: bool
    output: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
