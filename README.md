# Local AI Assistant (Ollama-only, Windows-ready)

Production-quality local personal AI assistant with a premium desktop UI,
voice-first interaction, local memory/RAG, and permissioned skills. Everything
is local-only and bound to 127.0.0.1. No cloud calls. No self-modifying code.

## Architecture

```
backend/  -> FastAPI + Ollama client + RAG + skills + audit logs
ui/       -> React + Tailwind (chat, sessions, settings, logs)
desktop/  -> Tauri v2 shell (tray + global shortcut + window mgmt)
```

## Requirements

- Windows 11
- Ollama installed and running locally
- Python 3.11+
- Node.js 20+ (for UI)
- Rust toolchain (for Tauri)

## Quick Start

### 1) Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m app
```

API binds to `127.0.0.1:8765` by default.

### 2) UI (React + Tailwind)

```bash
cd ui
npm install
npm run dev
```

### 3) Desktop (Tauri)

```bash
cd desktop
cargo install tauri-cli --version "^2"
cd src-tauri
cargo tauri dev
```

## Windows Task Scheduler (Daemon Mode)

Daemon mode runs background dreams/reflections without UI.

**Manual steps:**
1. Open Task Scheduler.
2. Create Task -> Trigger: At log on.
3. Action: Start a program.
4. Program: `python`
5. Arguments: `-m app.daemon`
6. Start in: `C:\path\to\repo\backend`

**schtasks example (Microsoft docs):**

```cmd
schtasks /Create /SC ONLOGON /TN "LocalAIAssistantDaemon" /TR "C:\Python311\python.exe -m app.daemon" /F /RL HIGHEST /RU "%USERNAME%"
```

Reference: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks-create

## Ollama Integration

- Models list: `GET http://127.0.0.1:11434/api/tags`
- Chat: `POST http://127.0.0.1:11434/api/chat`
- Embeddings: `POST http://127.0.0.1:11434/api/embed`

Base URL is configurable in `backend/data/config.json`.

## API Contract (Local-only)

- GET `/health`
- GET `/models` (supports `?health=true` ping)
- GET `/config`
- POST `/config`
- WS `/ws/chat`
- POST `/chat`
- POST `/voice/transcribe`
- POST `/voice/speak`
- POST `/rag/ingest`
- POST `/rag/search`
- GET `/logs/audit?tail=N`
- GET `/logs/dreams?tail=N`
- GET `/logs/reflections?tail=N`

## Voice Pipeline

Local-only voice is optional and toggleable. Install extras if needed:

- faster-whisper (STT)
- silero-vad (VAD)
- openwakeword (wake word)
- piper (TTS) or Windows SAPI fallback

Install voice extras:

```bash
cd backend
pip install -r requirements-voice.txt
```

Configure in `config.json`:

```json
{
  "voice": {
    "enabled": true,
    "hands_free": false,
    "wake_word_enabled": false,
    "piper_path": "C:\\path\\to\\piper.exe",
    "piper_model": "C:\\path\\to\\en_US-amy.onnx"
  }
}
```

## Local Memory + RAG

- SQLite for sessions/messages
- SQLite + hnswlib vector index
- Ingest via `/rag/ingest` or the Knowledge Ingest skill
- Retrieval injected into chat with in-memory citations

## Skills System

`backend/skills/<name>/manifest.json` + `skill.py`.

Built-in skills:
- `file_explorer` (read-only)
- `dev_assistant` (allowlisted terminal commands)
- `knowledge_ingest` (adds docs to RAG)

All skills are permission-gated and audited.

## Dream -> Reflect -> Improve

- Dreams (daily): LLM-only hypothetical scenarios, stored in `dream_journal.jsonl`
- Reflections (weekly): analyze dreams + audit log, propose config updates only
- Config diffs stored in `backend/data/config_diffs/`
- UI can review/rollback by restoring prior config

No source code is modified by these loops.

## Security & Auditability

- All services bind to 127.0.0.1
- Tools OFF by default
- File writes are safe-write (backup + atomic rename)
- Terminal allowlist only
- JSONL audit logs: `backend/data/audit_log.jsonl`

## Tests

Run backend tests:

```bash
cd backend
pytest
```

### Latest test output

```
<paste test output here>
```
