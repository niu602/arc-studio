"""Central configuration for the ARC Studio backend.

All values can be overridden via environment variables (loaded from a local
``.env`` file next to the backend root — see ``app/main.py`` bootstrap). The
ARC compiler ships inside this repository under ``../compiler`` so the whole
project is self-contained; point ``COMPILER_PYTHON`` / ``COMPILER_MAIN`` at
your own checkout if you prefer to use an external copy.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# backend/app/config.py -> backend/ is two levels up.
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
TASKS_DIR: Path = BACKEND_DIR / "tasks"

# The ARC compiler is vendored inside the project (arc-studio/compiler), so
# the repo is portable: copy the whole directory and it keeps working.
# Environment variables still take precedence for custom setups.
COMPILER_DIR: Path = BACKEND_DIR.parent / "compiler"
COMPILER_PYTHON: str = os.getenv(
    "COMPILER_PYTHON",
    str(COMPILER_DIR / ".venv" / "Scripts" / "python.exe"),
)
COMPILER_MAIN: str = os.getenv(
    "COMPILER_MAIN",
    str(COMPILER_DIR / "src" / "main.py"),
)

# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------
APP_TYPE_DEFAULT: str = os.getenv("ARC_APP_TYPE", "web")
# Each running web preview gets its own port, starting here and incrementing.
WEB_PORT_START: int = int(os.getenv("ARC_WEB_PORT_START", "3301"))
# Ring buffer size for per-task logs.
MAX_LOGS: int = int(os.getenv("ARC_MAX_LOGS", "1000"))
# Max seconds a single compilation may run before it is force-killed.
COMPILE_TIMEOUT_SECONDS: int = int(os.getenv("ARC_COMPILE_TIMEOUT", "7200"))

# Per-node estimated cost (CNY) charged when a node reaches a terminal state.
# Used by the live cost panel so real compilations show a non-zero number,
# consistent with the demo-mode figures (~¥0.01-0.02 per node).
NODE_COST_BY_STAGE: dict[str, float] = {
    "DESIGN": 0.010,
    "IMPLEMENT": 0.015,
    "TEST": 0.006,
}

# Lightweight persistence: task metadata (no API keys, no live processes) is
# snapshotted here so /api/history survives a backend restart.
PERSIST_INDEX_PATH: Path = TASKS_DIR / "index.json"

# ---------------------------------------------------------------------------
# CORS (frontend Vite dev server)
# ---------------------------------------------------------------------------
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# Default LLM settings (used by /api/generate-tree when the caller does not
# supply an API key / base url; if both are empty the service falls back to a
# built-in mock requirement tree).
# ---------------------------------------------------------------------------
DEFAULT_OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DEFAULT_OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
# Per-stage default models (must match the ARC compiler's env vars).
DEFAULT_DESIGNER_MODEL: str = os.getenv("ARC_MODEL_INTERFACE_DESIGNER", "deepseek-v4-pro")
DEFAULT_TEST_MODEL: str = os.getenv("ARC_MODEL_TEST_GENERATOR", "qwen3.7-plus")
DEFAULT_DEVELOPER_MODEL: str = os.getenv("ARC_MODEL_TEST_DRIVEN_DEVELOPER", "deepseek-v4-flash")
# chat_completions | responses
ARC_OPENAI_API_MODE: str = os.getenv("ARC_OPENAI_API_MODE", "chat_completions")


def compiler_available() -> bool:
    """True when the vendored (or overridden) compiler interpreter + main exist."""
    return Path(COMPILER_PYTHON).is_file() and Path(COMPILER_MAIN).is_file()


def ensure_directories() -> None:
    """Create runtime directories that must exist before requests arrive."""
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
