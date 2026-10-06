"""Demo-mode download endpoint: package the voice-calendar project as a zip.

The source project is vendored inside the repository at
``backend/demo_resources/voice-calendar`` so the demo keeps working on any
machine. Set ``VOICE_CALENDAR_SOURCE_DIR`` to point at an external checkout if
you want to package a newer copy. If neither exists the endpoint returns a
small README zip instead of a 404, so the demo never breaks.
"""

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api", tags=["demo"])

# backend/app/routers/demo.py -> backend/ is three levels up.
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEMO_RESOURCES_DIR = BACKEND_DIR / "demo_resources"

# Source project to package for the demo download (env override supported).
SOURCE_DIR = Path(
    os.getenv(
        "VOICE_CALENDAR_SOURCE_DIR",
        str(DEMO_RESOURCES_DIR / "voice-calendar"),
    )
)

# Directory names to exclude anywhere in the tree.
EXCLUDED_DIR_PARTS = {
    "node_modules",
    "target",
    ".idea",
    ".vscode",
    ".git",
    ".mvn",
    ".vite",
    "__pycache__",
    "dist",
}
# Relative sub-path to exclude (frontend build output).
EXCLUDED_REL_PREFIXES = ("front/dist",)
# File suffixes / names to exclude (secrets + editor metadata).
EXCLUDED_SUFFIXES = (".iml",)
EXCLUDED_FILENAMES = (".env", ".env.example", ".env.local", ".env.production", ".env.development")


def _is_excluded(rel: Path) -> bool:
    parts = rel.parts
    if any(part in EXCLUDED_DIR_PARTS for part in parts):
        return True
    rel_str = rel.as_posix()
    if any(rel_str.startswith(prefix + "/") or rel_str == prefix for prefix in EXCLUDED_REL_PREFIXES):
        return True
    if rel.suffix in EXCLUDED_SUFFIXES:
        return True
    if rel.name in EXCLUDED_FILENAMES:
        return True
    return False


def _zip_source(source_dir: Path) -> StreamingResponse:
    """Zip a directory tree into a StreamingResponse (never raises on missing dirs)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if source_dir.is_dir():
            for file in source_dir.rglob("*"):
                if not file.is_file():
                    continue
                rel = file.relative_to(source_dir)
                if _is_excluded(rel):
                    continue
                zf.write(file, arcname=str(rel))
        else:
            zf.writestr(
                "README.txt",
                "ARC Studio 演示模式说明\n"
                "========================\n"
                "演示模式的作品源码未随本包分发。\n\n"
                "演示模式展示的是「语音日历」应用从自然语言到完整项目的编译闭环，"
                "可在页面的「应用预览」中直接体验登录页与月历视图。\n\n"
                "真实编译模式需要配置 OpenAI 兼容 API Key（见 README），"
                "编译器仓库已内置在本项目 compiler/ 目录。\n",
            )
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="voice-calendar-project.zip"',
        },
    )


@router.get("/demo-download")
def demo_download() -> StreamingResponse:
    """Stream the voice-calendar project as a zip (demo mode)."""
    return _zip_source(SOURCE_DIR)
