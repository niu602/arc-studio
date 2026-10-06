"""Compilation lifecycle endpoints: start, status, result, cancel, download."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models import (
    CancelResponse,
    CompileRequest,
    CompileResponse,
    ResultSummary,
    TaskResultResponse,
    TaskStatus,
    TaskStatusResponse,
    TestResultItem,
)
from app.services.compiler import CompilerService
from app.services.task_manager import TaskRecord, get_task_manager
from app.services.tree_generator import TreeGeneratorService
from app.utils.yaml_helper import write_yaml
import yaml

router = APIRouter(prefix="/api", tags=["compile"])

_tm = get_task_manager()
_compiler = CompilerService()
_tree_service = TreeGeneratorService()


def _require_record(task_id: str) -> TaskRecord:
    record = _tm.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return record


# ---------------------------------------------------------------------------
# POST /api/compile
# ---------------------------------------------------------------------------
@router.post("/compile", response_model=CompileResponse)
def start_compilation(req: CompileRequest) -> CompileResponse:
    # 0. Map frontend app_type to compiler-supported types.
    #    web -> web, mobile -> android, anything else falls back to web.
    app_type_map = {"web": "web", "mobile": "android"}
    app_type = app_type_map.get(req.app_type.lower(), "web")

    # 1. Resolve the requirement YAML (explicit, or generated from NL).
    generated_nodes = 0
    if req.requirement_yaml and req.requirement_yaml.strip():
        yaml_text = req.requirement_yaml
    else:
        tree = _tree_service.generate(
            requirement=req.requirement_text,
            app_type=app_type,
            api_key=req.api_key,
            base_url=req.base_url,
            model=req.model,
        )
        yaml_text = tree.requirement_yaml
        generated_nodes = len(tree.nodes)

    # Per-stage models from the request (optional; empty -> compiler defaults).
    models = req.models
    designer = (models.design if models else None) or ""
    tester = (models.test if models else None) or ""
    developer = (models.development if models else None) or ""

    # 2. Create the task record (allocates dirs and a web port).
    record = _tm.create_task(
        app_type=app_type,
        api_key=req.api_key,
        base_url=req.base_url,
        model=req.model or "",
        designer_model=designer,
        test_model=tester,
        developer_model=developer,
        total_nodes=generated_nodes,
    )

    # 3. Persist the requirement YAML.
    try:
        write_yaml(str(record.requirement_path), yaml.safe_load(yaml_text))
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"需求 YAML 解析失败: {exc}")

    # 4. Launch the compiler in a background thread.
    _compiler.start_in_background(record)

    return CompileResponse(
        task_id=record.task_id,
        status=record.status,
        message="编译任务已创建",
    )


# ---------------------------------------------------------------------------
# GET /api/status/{task_id}
# ---------------------------------------------------------------------------
@router.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_status(task_id: str, since: Optional[int] = Query(default=None, ge=0)) -> TaskStatusResponse:
    record = _require_record(task_id)
    return TaskStatusResponse(**_tm.status_snapshot(record, since=since))


# ---------------------------------------------------------------------------
# GET /api/result/{task_id}
# ---------------------------------------------------------------------------
def _scan_test_results(output_dir: Path) -> list[TestResultItem]:
    """Best-effort scan of the output dir for test-result JSON files."""
    results: list[TestResultItem] = []
    if not output_dir.exists():
        return results
    for path in output_dir.rglob("*.json"):
        name = path.name.lower()
        if "test" not in name and "result" not in name:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Accept a list of {name, status, error?} or {tests: [...]}.
        items = data if isinstance(data, list) else data.get("tests") or data.get("results") or []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                results.append(
                    TestResultItem(
                        name=str(item.get("name", item.get("title", "未命名测试"))),
                        status=str(item.get("status", item.get("state", "UNKNOWN"))).upper(),
                        error=item.get("error"),
                    )
                )
        if results:
            break
    return results


@router.get("/result/{task_id}", response_model=TaskResultResponse)
def get_result(task_id: str) -> TaskResultResponse:
    record = _require_record(task_id)

    nodes = list(record.nodes.values())
    passed = sum(1 for n in nodes if n["status"] == "PASSED")
    failed = sum(1 for n in nodes if n["status"] == "FAILED")

    # Preview URL only when compile succeeded and the preview process is alive.
    preview_url = ""
    if record.status == TaskStatus.COMPLETED and record.preview_process is not None:
        try:
            if record.preview_process.poll() is None:  # type: ignore[union-attr]
                preview_url = f"http://localhost:{record.web_port}"
        except Exception:  # noqa: BLE001
            preview_url = ""

    return TaskResultResponse(
        task_id=record.task_id,
        status=record.status,
        preview_url=preview_url,
        download_url=f"/api/download/{record.task_id}",
        test_results=_scan_test_results(record.output_dir),
        output_dir=str(record.output_dir),
        summary=ResultSummary(
            total_nodes=record.total_nodes or len(nodes),
            passed_nodes=passed,
            failed_nodes=failed,
            total_time_seconds=record.elapsed_seconds,
            total_cost=record.estimated_cost,
        ),
    )


# ---------------------------------------------------------------------------
# POST /api/cancel/{task_id}
# ---------------------------------------------------------------------------
@router.post("/cancel/{task_id}", response_model=CancelResponse)
def cancel_compilation(task_id: str) -> CancelResponse:
    record = _require_record(task_id)
    message = _compiler.cancel(record)
    return CancelResponse(task_id=task_id, status=record.status, message=message)


# ---------------------------------------------------------------------------
# GET /api/download/{task_id}
# ---------------------------------------------------------------------------
@router.get("/download/{task_id}")
def download_result(task_id: str) -> StreamingResponse:
    record = _require_record(task_id)
    if not record.output_dir.exists():
        raise HTTPException(status_code=404, detail="输出目录不存在，暂无可下载内容")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in record.output_dir.rglob("*"):
            if not file.is_file():
                continue
            # Skip regenerable build output; it is recreated by `npm install`.
            rel_parts = file.relative_to(record.output_dir).parts
            if any(part in ("node_modules", ".next", ".cache") for part in rel_parts):
                continue
            zf.write(file, arcname=str(file.relative_to(record.output_dir)))
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="arc_{task_id}.zip"'},
    )


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------
@router.get("/history")
def list_history(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    """Return a brief list of in-memory compilation tasks (newest first)."""
    from datetime import datetime

    records = _tm.list_tasks()

    def _summary(record: TaskRecord) -> dict:
        nodes = list(record.nodes.values())
        passed = sum(1 for n in nodes if n["status"] == "PASSED")
        failed = sum(1 for n in nodes if n["status"] == "FAILED")
        return {
            "task_id": record.task_id,
            "app_type": record.app_type,
            "status": record.status.value,
            "created_at": datetime.fromtimestamp(record.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            "total_nodes": record.total_nodes or len(nodes),
            "passed_nodes": passed,
            "failed_nodes": failed,
        }

    summaries = [_summary(r) for r in records]
    summaries.sort(key=lambda s: s["created_at"], reverse=True)
    return summaries[:limit]
