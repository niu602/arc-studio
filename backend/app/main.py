"""ARC Studio backend — FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 0) Bootstrapping (must run BEFORE any project import):
#    - sys.path fix so `uvicorn app.main:app` works regardless of CWD.
#    - load backend/.env into the environment before config.py reads it.
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:  # python-dotenv is a declared dependency; degrade gracefully if missing.
    from dotenv import load_dotenv

    load_dotenv(_BACKEND_DIR / ".env", override=False)
except ImportError:  # pragma: no cover
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import compile as compile_router
from app.routers import demo as demo_router
from app.routers import tree as tree_router

config.ensure_directories()

app = FastAPI(
    title="ARC Studio API",
    description="包装 ARC 编译器的 REST 后端：自然语言转需求树、异步编译、状态查询、结果下载。",
    version="0.1.0",
)

# CORS — allow the Vite dev server (and any local origins configured via env).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tree_router.router)
app.include_router(compile_router.router)
app.include_router(demo_router.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "arc-studio-backend",
        "compiler_available": config.compiler_available(),
    }


@app.get("/", tags=["meta"])
def index() -> dict[str, str]:
    return {"service": "ARC Studio API", "docs": "/docs"}
