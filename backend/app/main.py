from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .audit import AuditLogger
from .config_store import ConfigStore
from .dreams import Dreamer, Reflector
from .logs import read_tail
from .models import (
    AppConfig,
    ApprovalRequest,
    ChatRequest,
    ChatResponse,
    RagIngestRequest,
    RagSearchRequest,
    RouterTestRequest,
)
from .ollama import OllamaClient
from .policies import ApprovalStore, PolicyEngine
from .rag import RagIndex, sanitize_paths
from .router import choose_model
from .scheduler import run_scheduler
from .skills import SkillContext, SkillManager
from .storage import SqliteStore
from .voice import VoicePipeline


def create_app(
    data_dir: Path | None = None,
    config_store: ConfigStore | None = None,
    ollama_client: OllamaClient | None = None,
    store: SqliteStore | None = None,
    rag_index: RagIndex | None = None,
    audit_logger: AuditLogger | None = None,
    approvals: ApprovalStore | None = None,
) -> FastAPI:
    app = FastAPI(title="Local AI Assistant", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    root_dir = Path(__file__).resolve().parents[1]
    data_dir = data_dir or Path(os.environ.get("ASSISTANT_DATA_DIR", root_dir / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)

    config_store = config_store or ConfigStore(data_dir)
    config = config_store.load()
    approvals = approvals or ApprovalStore()
    policy = PolicyEngine(config.permissions, approvals)
    audit_logger = audit_logger or AuditLogger(data_dir, config.audit)
    store = store or SqliteStore(data_dir)
    ollama_client = ollama_client or OllamaClient(config.ollama_base_url)
    rag_index = rag_index or RagIndex(data_dir, config.rag, ollama_client, store)
    voice_pipeline = VoicePipeline(config.voice)
    dreamer = Dreamer(data_dir, ollama_client, config_store)
    reflector = Reflector(data_dir, ollama_client, config_store)

    def context_factory() -> SkillContext:
        current = app.state.config_store.load()
        current_policy = PolicyEngine(current.permissions, app.state.approvals)
        current_audit = AuditLogger(app.state.data_dir, current.audit)
        return SkillContext(current_policy, current_audit, app.state.rag)

    skills_dir = root_dir / "skills"
    skill_manager = SkillManager(skills_dir, context_factory)

    app.state.data_dir = data_dir
    app.state.config_store = config_store
    app.state.config = config
    app.state.approvals = approvals
    app.state.policy = policy
    app.state.audit = audit_logger
    app.state.store = store
    app.state.ollama = ollama_client
    app.state.rag = rag_index
    app.state.voice = voice_pipeline
    app.state.skill_manager = skill_manager
    app.state.dreamer = dreamer
    app.state.reflector = reflector

    @app.on_event("startup")
    async def _start_scheduler() -> None:
        asyncio.create_task(run_scheduler(app))

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "mode": os.environ.get("ASSISTANT_MODE", "desktop")}

    @app.get("/models")
    async def models(health: bool = False) -> dict[str, Any]:
        try:
            tags = await app.state.ollama.list_models()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not health:
            return {"models": tags}
        health_map: dict[str, float] = {}
        for tag in tags:
            name = tag.get("name")
            if not name:
                continue
            try:
                health_map[name] = await app.state.ollama.ping_model(name)
            except Exception:
                health_map[name] = -1
        return {"models": tags, "health": health_map}

    @app.get("/config")
    async def get_config() -> dict[str, Any]:
        return app.state.config_store.load().model_dump(mode="json")

    @app.post("/config")
    async def update_config(payload: dict[str, Any]) -> dict[str, Any]:
        config = AppConfig.model_validate(payload)
        app.state.config_store.save(config)
        app.state.config = config
        app.state.ollama = OllamaClient(config.ollama_base_url)
        app.state.policy = PolicyEngine(config.permissions, app.state.approvals)
        app.state.audit = AuditLogger(app.state.data_dir, config.audit)
        app.state.rag = RagIndex(app.state.data_dir, config.rag, app.state.ollama, app.state.store)
        app.state.voice = VoicePipeline(config.voice)
        return config.model_dump(mode="json")

    @app.post("/approvals")
    async def add_approval(request: ApprovalRequest) -> dict[str, Any]:
        app.state.approvals.add(request.scope, request.expires_at)
        return {"status": "ok", "scope": request.scope}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        config = app.state.config_store.load()
        installed = [model["name"] for model in await app.state.ollama.list_models()]
        decision = choose_model(
            config,
            installed,
            [message.content for message in request.messages],
            speed_quality=request.speed_quality,
            requested_task=request.task_type,
            override_model=request.model,
        )
        sources = []
        messages = [message.model_dump() for message in request.messages]
        if request.use_rag and config.rag.enabled:
            sources = await app.state.rag.search(request.messages[-1].content, config.rag.top_k)
            if sources:
                context_blob = "\n\n".join(
                    f"[{source['source_path']}] {source['content']}" for source in sources
                )
                messages.insert(0, {"role": "system", "content": f"Context:\n{context_blob}"})
        payload = {"model": decision.model, "messages": messages, "stream": False}
        response = await app.state.ollama.chat(payload)
        content = response.get("message", {}).get("content", "")
        if request.session_id:
            app.state.store.create_session(request.session_id)
            for message in request.messages:
                app.state.store.add_message(request.session_id, message.role, message.content, decision.model)
            app.state.store.add_message(request.session_id, "assistant", content, decision.model)
        app.state.audit.log(
            {
                "tool": "chat",
                "session_id": request.session_id,
                "model": decision.model,
                "routing_rule": decision.rule,
                "rag_used": bool(sources),
            }
        )
        return ChatResponse(model=decision.model, content=content, routing_rule=decision.rule, sources=sources)

    @app.websocket("/ws/chat")
    async def chat_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            payload = await websocket.receive_json()
            request = ChatRequest.model_validate(payload)
            config = app.state.config_store.load()
            installed = [model["name"] for model in await app.state.ollama.list_models()]
            decision = choose_model(
                config,
                installed,
                [message.content for message in request.messages],
                speed_quality=request.speed_quality,
                requested_task=request.task_type,
                override_model=request.model,
            )
            await websocket.send_json(
                {"type": "routing", "model": decision.model, "rule": decision.rule, "task_type": decision.task_type}
            )
            sources = []
            messages = [message.model_dump() for message in request.messages]
            if request.use_rag and config.rag.enabled:
                sources = await app.state.rag.search(request.messages[-1].content, config.rag.top_k)
                if sources:
                    context_blob = "\n\n".join(
                        f"[{source['source_path']}] {source['content']}" for source in sources
                    )
                    messages.insert(0, {"role": "system", "content": f"Context:\n{context_blob}"})
                    await websocket.send_json({"type": "rag", "sources": sources})
            payload = {"model": decision.model, "messages": messages, "stream": True}
            assistant_chunks = []
            async for chunk in app.state.ollama.stream_chat(payload):
                if chunk.get("done"):
                    break
                token = chunk.get("message", {}).get("content", "")
                if token:
                    assistant_chunks.append(token)
                    await websocket.send_json({"type": "token", "content": token})
            content = "".join(assistant_chunks)
            if request.session_id:
                app.state.store.create_session(request.session_id)
                for message in request.messages:
                    app.state.store.add_message(request.session_id, message.role, message.content, decision.model)
                app.state.store.add_message(request.session_id, "assistant", content, decision.model)
            app.state.audit.log(
                {
                    "tool": "chat_stream",
                    "session_id": request.session_id,
                    "model": decision.model,
                    "routing_rule": decision.rule,
                    "rag_used": bool(sources),
                }
            )
            await websocket.send_json({"type": "done"})
        except WebSocketDisconnect:
            return
        except Exception as exc:
            await websocket.send_json({"type": "error", "error": str(exc)})
            await websocket.close(code=1011)

    @app.post("/voice/transcribe")
    async def voice_transcribe(audio: UploadFile = File(...)) -> dict[str, Any]:
        config = app.state.config_store.load()
        if not config.voice.enabled:
            raise HTTPException(status_code=403, detail="Voice features disabled")
        audio_bytes = await audio.read()
        try:
            result = app.state.voice.transcribe(audio_bytes)
        except Exception as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        return result

    @app.post("/voice/speak")
    async def voice_speak(payload: dict[str, Any]) -> Response:
        config = app.state.config_store.load()
        if not config.voice.enabled:
            raise HTTPException(status_code=403, detail="Voice features disabled")
        text = payload.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        try:
            audio_bytes = app.state.voice.speak(text)
        except Exception as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        return Response(content=audio_bytes, media_type="audio/wav")

    @app.post("/rag/ingest")
    async def rag_ingest(request: RagIngestRequest) -> dict[str, Any]:
        config = app.state.config_store.load()
        policy = PolicyEngine(config.permissions, app.state.approvals)
        if not config.rag.enabled:
            raise HTTPException(status_code=403, detail="RAG disabled")
        paths = sanitize_paths(request.paths)
        for path in paths:
            decision = policy.check_file_read(path)
            if not decision.allowed:
                raise HTTPException(status_code=403, detail=decision.model_dump())
        result = await app.state.rag.ingest_paths(paths)
        app.state.audit.log({"tool": "rag_ingest", "paths": paths, "decision": "allowed"})
        return result

    @app.post("/rag/search")
    async def rag_search(request: RagSearchRequest) -> dict[str, Any]:
        config = app.state.config_store.load()
        top_k = request.top_k or config.rag.top_k
        results = await app.state.rag.search(request.query, top_k)
        return {"results": results}

    @app.post("/router/test")
    async def router_test(request: RouterTestRequest) -> dict[str, Any]:
        config = app.state.config_store.load()
        installed = [model["name"] for model in await app.state.ollama.list_models()]
        decision = choose_model(
            config,
            installed,
            [request.message],
            speed_quality=request.speed_quality,
            requested_task=request.task_type,
            override_model=request.model,
        )
        return {"model": decision.model, "rule": decision.rule, "task_type": decision.task_type}

    @app.get("/logs/audit")
    async def audit_logs(tail: int = 200) -> dict[str, Any]:
        path = app.state.data_dir / "audit_log.jsonl"
        return {"entries": read_tail(path, tail)}

    @app.get("/logs/dreams")
    async def dream_logs(tail: int = 50) -> dict[str, Any]:
        path = app.state.data_dir / "dream_journal.jsonl"
        return {"entries": read_tail(path, tail)}

    @app.get("/logs/reflections")
    async def reflection_logs(tail: int = 50) -> dict[str, Any]:
        path = app.state.data_dir / "reflection_journal.jsonl"
        return {"entries": read_tail(path, tail)}

    @app.get("/skills")
    async def list_skills() -> dict[str, Any]:
        skills = [skill.__dict__ for skill in app.state.skill_manager.list_skills()]
        return {"skills": skills}

    @app.post("/skills/run")
    async def run_skill(payload: dict[str, Any]) -> dict[str, Any]:
        skill_name = payload.get("skill")
        args = payload.get("input", {})
        if not skill_name:
            raise HTTPException(status_code=400, detail="Skill name required")
        config = app.state.config_store.load()
        policy = PolicyEngine(config.permissions, app.state.approvals)
        decision = policy.check_skill(skill_name)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.model_dump())
        result = await app.state.skill_manager.run(skill_name, args)
        app.state.audit.log({"tool": "skill", "skill": skill_name, "decision": "allowed"})
        return result.model_dump(mode="json")

    return app


app = create_app()
