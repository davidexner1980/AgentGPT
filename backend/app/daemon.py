from __future__ import annotations

import asyncio
import os

import uvicorn

from .main import create_app
from .scheduler import run_scheduler


async def main() -> None:
    os.environ["ASSISTANT_MODE"] = "daemon"
    app = create_app()
    await run_scheduler(app)


if __name__ == "__main__":
    asyncio.run(main())
