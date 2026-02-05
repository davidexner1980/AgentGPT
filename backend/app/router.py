from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import AppConfig, RouterRule


@dataclass
class RoutingDecision:
    model: str
    rule: str | None
    task_type: str


def detect_task_type(messages: Iterable[str], requested: str | None = None) -> str:
    if requested:
        return requested
    combined = " ".join(messages).lower()
    if "code" in combined or "bug" in combined or "stack trace" in combined:
        return "coding"
    if "why" in combined or "reason" in combined or "explain" in combined:
        return "reasoning"
    return "qa"


def choose_model(
    config: AppConfig,
    installed: list[str],
    messages: Iterable[str],
    speed_quality: int | None = None,
    requested_task: str | None = None,
    override_model: str | None = None,
) -> RoutingDecision:
    if override_model:
        return RoutingDecision(model=override_model, rule="override", task_type=requested_task or "any")
    task_type = detect_task_type(messages, requested_task)
    quality = speed_quality if speed_quality is not None else config.routing.speed_quality
    rules = config.routing.rules
    for rule in rules:
        if rule.task_type not in (task_type, "any"):
            continue
        if not (rule.min_quality <= quality <= rule.max_quality):
            continue
        if rule.match_keywords:
            combined = " ".join(messages).lower()
            if not any(keyword.lower() in combined for keyword in rule.match_keywords):
                continue
        chosen = _pick_installed(rule.model, rule.fallback_model, installed)
        if chosen:
            return RoutingDecision(model=chosen, rule=rule.name, task_type=task_type)
    fallback = _pick_installed(config.routing.default_model, None, installed)
    if fallback:
        return RoutingDecision(model=fallback, rule="config_default", task_type=task_type)
    if installed:
        return RoutingDecision(model=installed[0], rule="first_installed", task_type=task_type)
    raise RuntimeError("No installed Ollama models available")


def _pick_installed(primary: str | None, fallback: str | None, installed: list[str]) -> str | None:
    if primary and primary in installed:
        return primary
    if fallback and fallback in installed:
        return fallback
    return None
