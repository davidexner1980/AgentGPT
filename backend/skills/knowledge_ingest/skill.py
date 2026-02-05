from __future__ import annotations


async def run(context, payload):
    paths = payload.get("paths", [])
    if not paths:
        return {"success": False, "error": "Paths required"}
    return await context.rag_ingest(paths)
