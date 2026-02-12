from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import numpy as np

from .models import RagConfig
from .ollama import OllamaClient
from .storage import SqliteStore

try:
    import hnswlib
except ImportError:  # pragma: no cover - optional dependency
    hnswlib = None


class RagIndex:
    def __init__(
        self,
        data_dir: Path,
        config: RagConfig,
        ollama: OllamaClient,
        store: SqliteStore,
    ) -> None:
        self.data_dir = data_dir
        self.config = config
        self.ollama = ollama
        self.store = store
        self.index_path = data_dir / "rag_index.bin"
        self._index = None
        self._load_index()

    def _load_index(self) -> None:
        if hnswlib is None:
            self._index = None
            return
        index = hnswlib.Index(space="cosine", dim=self.config.embedding_dim)
        if self.index_path.exists():
            index.load_index(str(self.index_path))
        else:
            index.init_index(max_elements=100000, ef_construction=200, M=16)
            index.set_ef(50)
        self._index = index

    def _persist(self) -> None:
        if self._index is None:
            return
        self._index.save_index(str(self.index_path))

    async def ingest_paths(self, paths: list[str]) -> dict[str, Any]:
        indexed = []
        skipped = []
        for path in paths:
            path_obj = Path(path).expanduser()
            if path_obj.is_dir():
                for file_path in path_obj.rglob("*"):
                    if file_path.is_file():
                        await self._ingest_file(file_path, indexed, skipped)
            elif path_obj.is_file():
                await self._ingest_file(path_obj, indexed, skipped)
            else:
                skipped.append(path)
        self._persist()
        return {"indexed": indexed, "skipped": skipped}

    async def _ingest_file(self, file_path: Path, indexed: list[str], skipped: list[str]) -> None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            skipped.append(str(file_path))
            return
        if not content.strip():
            skipped.append(str(file_path))
            return
        hash_value = hashlib.sha256(content.encode("utf-8")).hexdigest()
        doc_id = self.store.insert_doc(str(file_path), hash_value)
        chunks = self._chunk_text(content)
        embeddings = await self.ollama.embed(self.config.embedding_model, chunks)
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = self.store.insert_chunk(doc_id, idx, chunk, str(file_path))
            self._add_vector(chunk_id, embedding)
        indexed.append(str(file_path))

    def _chunk_text(self, text: str) -> list[str]:
        size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = max(0, end - overlap)
        return chunks

    def _add_vector(self, vector_id: int, embedding: list[float]) -> None:
        if self._index is None:
            return
        vec = np.array(embedding, dtype=np.float32)
        self._index.add_items(vec, np.array([vector_id], dtype=np.int64))

    async def search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if self._index is None:
            return []
        embeddings = await self.ollama.embed(self.config.embedding_model, [query])
        vec = np.array(embeddings[0], dtype=np.float32)
        labels, distances = self._index.knn_query(vec, k=top_k)
        scored = []
        ids = []
        for index, item in enumerate(labels[0]):
            chunk_id = int(item)
            if chunk_id < 0:
                continue
            ids.append(chunk_id)
            scored.append({"id": chunk_id, "score": 1 - float(distances[0][index])})
        chunks = {chunk["id"]: chunk for chunk in self.store.get_chunks(ids)}
        merged = []
        for entry in scored:
            chunk = chunks.get(entry["id"])
            if chunk:
                merged.append({**chunk, "score": entry["score"]})
        return merged

    def forget_doc(self, doc_id: int) -> None:
        chunk_ids = self.store.delete_doc(doc_id)
        if self._index is None:
            return
        if hasattr(self._index, "mark_deleted"):
            for chunk_id in chunk_ids:
                self._index.mark_deleted(chunk_id)
            self._persist()


def sanitize_paths(paths: list[str]) -> list[str]:
    return [os.path.abspath(os.path.expanduser(path)) for path in paths]
