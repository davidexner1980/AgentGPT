from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SqliteStore:
    def __init__(self, data_dir: Path) -> None:
        self.db_path = data_dir / "assistant.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    model TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT,
                    hash TEXT,
                    added_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER,
                    chunk_index INTEGER,
                    content TEXT,
                    source_path TEXT,
                    added_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rag_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )

    def create_session(self, session_id: str, title: str | None = None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
                (session_id, title, self._now()),
            )

    def add_message(self, session_id: str, role: str, content: str, model: str | None) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, model, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, model, self._now()),
            )

    def insert_doc(self, path: str, hash_value: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO rag_docs (path, hash, added_at) VALUES (?, ?, ?)",
                (path, hash_value, self._now()),
            )
            return int(cursor.lastrowid)

    def insert_chunk(self, doc_id: int, chunk_index: int, content: str, source_path: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO rag_chunks (doc_id, chunk_index, content, source_path, added_at) VALUES (?, ?, ?, ?, ?)",
                (doc_id, chunk_index, content, source_path, self._now()),
            )
            return int(cursor.lastrowid)

    def get_chunks(self, chunk_ids: list[int]) -> list[dict[str, Any]]:
        if not chunk_ids:
            return []
        placeholder = ",".join("?" for _ in chunk_ids)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT id, content, source_path FROM rag_chunks WHERE id IN ({placeholder})",
                chunk_ids,
            )
            return [
                {"id": row[0], "content": row[1], "source_path": row[2]} for row in cursor.fetchall()
            ]

    def delete_doc(self, doc_id: int) -> list[int]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM rag_chunks WHERE doc_id = ?", (doc_id,))
            chunk_ids = [row[0] for row in cursor.fetchall()]
            conn.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM rag_docs WHERE id = ?", (doc_id,))
        return chunk_ids

    def _now(self) -> str:
        return datetime.now(tz=timezone.utc).isoformat()
