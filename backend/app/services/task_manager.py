"""In-memory async task manager (singleton).

Compilations are long-running (tens of minutes), so each task is executed in a
background thread that drives a ``subprocess.Popen`` against the ARC compiler.
All shared state is guarded by a lock; the HTTP layer only reads snapshots.

Task metadata (without API keys or live processes) is snapshotted to
``tasks/index.json`` on creation and on terminal state changes, and restored
on startup, so ``/api/history`` survives a backend restart.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from app import config
from app.models import LogEntry, NodeStatus, NodeStatusItem, Stage, TaskStats, TaskStatus


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class TaskRecord:
    task_id: str
    task_dir: Path
    output_dir: Path
    requirement_path: Path
    web_port: int
    app_type: str = "web"
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    # Populated by the compiler runner.
    process: Optional[object] = None  # subprocess.Popen
    logs: deque = field(default_factory=lambda: deque(maxlen=config.MAX_LOGS))
    nodes: dict[str, dict] = field(default_factory=dict)  # node_id -> {status, stage}
    total_nodes: int = 0
    # Live estimate accumulated per finished node (see NODE_COST_BY_STAGE).
    estimated_cost: float = 0.0

    # Credentials carried for env injection / result bookkeeping.
    # NOTE: intentionally NOT persisted to index.json.
    api_key: str = ""
    base_url: str = ""
    model: str = ""

    # Per-stage models (preferred over the legacy `model` field).
    designer_model: str = ""
    test_model: str = ""
    developer_model: str = ""

    # Preview server process (started after a successful compile).
    preview_process: Optional[object] = None

    @property
    def elapsed_seconds(self) -> float:
        end = self.finished_at or time.time()
        start = self.started_at or self.created_at
        return round(end - start, 1)


class TaskManager:
    """Thread-safe singleton registry of compilation tasks."""

    _instance: Optional["TaskManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "TaskManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._next_port = config.WEB_PORT_START
        config.ensure_directories()
        self._restore_persisted()

    # ------------------------------------------------------------------
    # Creation / lookup
    # ------------------------------------------------------------------
    def create_task(
        self,
        *,
        app_type: str,
        api_key: str,
        base_url: str,
        model: str,
        designer_model: str = "",
        test_model: str = "",
        developer_model: str = "",
        total_nodes: int = 0,
    ) -> TaskRecord:
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        with self._lock:
            web_port = self._next_port
            self._next_port += 1
        task_dir = config.TASKS_DIR / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        output_dir = task_dir / "output"
        output_dir.mkdir(exist_ok=True)
        requirement_path = task_dir / "requirements.yaml"

        record = TaskRecord(
            task_id=task_id,
            task_dir=task_dir,
            output_dir=output_dir,
            requirement_path=requirement_path,
            web_port=web_port,
            app_type=app_type,
            api_key=api_key,
            base_url=base_url,
            model=model,
            designer_model=designer_model,
            test_model=test_model,
            developer_model=developer_model,
            total_nodes=total_nodes,
        )
        with self._lock:
            self._tasks[task_id] = record
            self._persist_locked()
        return record

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        with self._lock:
            return list(self._tasks.values())

    # ------------------------------------------------------------------
    # Mutation helpers (all take the record directly; record fields are
    # mutated under the manager lock where concurrent reads are possible).
    # ------------------------------------------------------------------
    def set_status(self, record: TaskRecord, status: TaskStatus) -> None:
        with self._lock:
            record.status = status
            if status in (TaskStatus.RUNNING,) and record.started_at is None:
                record.started_at = time.time()
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                record.finished_at = time.time()
                self._persist_locked()

    def append_log(self, record: TaskRecord, level: str, message: str) -> None:
        entry = {"timestamp": _now_str(), "level": level, "message": message}
        with self._lock:
            record.logs.append(entry)

    def update_node(
        self,
        record: TaskRecord,
        node_id: str,
        status: Optional[NodeStatus] = None,
        stage: Optional[Stage] = None,
    ) -> None:
        with self._lock:
            existing = record.nodes.setdefault(
                node_id, {"status": NodeStatus.PENDING.value, "stage": Stage.DESIGN.value}
            )
            prev_status = existing["status"]
            if status is not None:
                existing["status"] = status.value
            if stage is not None:
                existing["stage"] = stage.value
            # Charge the per-node estimated cost exactly once, when a node
            # first reaches a terminal state (PASSED / FAILED).
            if (
                status is not None
                and status.value in (NodeStatus.PASSED.value, NodeStatus.FAILED.value)
                and prev_status not in (NodeStatus.PASSED.value, NodeStatus.FAILED.value)
            ):
                stage_key = existing["stage"]
                record.estimated_cost = round(
                    record.estimated_cost + config.NODE_COST_BY_STAGE.get(stage_key, 0.010), 4
                )

    def set_total_nodes(self, record: TaskRecord, total: int) -> None:
        with self._lock:
            if total > record.total_nodes:
                record.total_nodes = total

    # ------------------------------------------------------------------
    # Snapshot (HTTP layer)
    # ------------------------------------------------------------------
    def status_snapshot(self, record: TaskRecord, since: Optional[int] = None) -> dict:
        with self._lock:
            logs = list(record.logs)
            nodes = [
                NodeStatusItem(id=nid, status=NodeStatus(info["status"]), stage=Stage(info["stage"]))
                for nid, info in sorted(record.nodes.items())
            ]
            completed = sum(
                1 for info in record.nodes.values() if info["status"] == NodeStatus.PASSED.value
            )
            total = record.total_nodes or max(len(record.nodes), 1)
            progress = int(completed / total * 100) if record.status == TaskStatus.RUNNING else (
                100 if record.status == TaskStatus.COMPLETED else 0
            )
            current_stage = self._current_stage_locked(record)
            elapsed = record.elapsed_seconds
            estimated_cost = record.estimated_cost

        log_models = [LogEntry(**e) for e in logs]
        if since is not None:
            log_models = log_models[since:]

        # First RUNNING node id (for the frontend's "current node" highlight).
        current_node = ""
        for nid, info in record.nodes.items():
            if info["status"] == NodeStatus.RUNNING.value:
                current_node = nid
                break

        return {
            "task_id": record.task_id,
            "status": record.status,
            "progress": max(0, min(progress, 100)),
            "current_stage": current_stage,
            "current_node": current_node,
            "nodes": [n.model_dump() for n in nodes],
            "logs": [l.model_dump() for l in log_models],
            "stats": TaskStats(
                completed_nodes=completed,
                total_nodes=record.total_nodes or len(record.nodes),
                elapsed_seconds=elapsed,
                estimated_cost=estimated_cost,
            ).model_dump(),
        }

    @staticmethod
    def _current_stage_locked(record: TaskRecord) -> str:
        stage_map = {
            Stage.DESIGN.value: "设计阶段",
            Stage.IMPLEMENT.value: "开发实现阶段",
            Stage.TEST.value: "测试阶段",
        }
        running = [info for info in record.nodes.values() if info["status"] == NodeStatus.RUNNING.value]
        if running:
            return stage_map.get(running[-1]["stage"], "编译进行中")
        if record.status == TaskStatus.PENDING:
            return "等待开始"
        if record.status == TaskStatus.COMPLETED:
            return "编译完成"
        if record.status == TaskStatus.FAILED:
            return "编译失败"
        if record.status == TaskStatus.CANCELLED:
            return "已取消"
        return "编译进行中"

    # ------------------------------------------------------------------
    # Lightweight persistence (metadata only — no keys, no live processes)
    # ------------------------------------------------------------------
    def _persist_locked(self) -> None:
        """Write a compact metadata snapshot. Failures are non-fatal."""
        try:
            payload = [self._record_to_dict(r) for r in self._tasks.values()]
            config.PERSIST_INDEX_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001 - persistence must never break requests
            pass

    @staticmethod
    def _record_to_dict(record: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": record.task_id,
            "task_dir": str(record.task_dir),
            "output_dir": str(record.output_dir),
            "requirement_path": str(record.requirement_path),
            "web_port": record.web_port,
            "app_type": record.app_type,
            "status": record.status.value,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "total_nodes": record.total_nodes,
            "estimated_cost": record.estimated_cost,
            "nodes": record.nodes,
            "logs": list(record.logs),
            "model": record.model,
            "designer_model": record.designer_model,
            "test_model": record.test_model,
            "developer_model": record.developer_model,
        }

    def _restore_persisted(self) -> None:
        """Rebuild task metadata from index.json. Keys and processes are not
        restored; tasks that were mid-flight are marked FAILED because their
        compiler process died with the previous server."""
        if not config.PERSIST_INDEX_PATH.is_file():
            return
        try:
            payload = json.loads(config.PERSIST_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return

        for item in payload:
            try:
                status = TaskStatus(item.get("status", "FAILED"))
                if status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    status = TaskStatus.FAILED
                record = TaskRecord(
                    task_id=item["task_id"],
                    task_dir=Path(item["task_dir"]),
                    output_dir=Path(item["output_dir"]),
                    requirement_path=Path(item["requirement_path"]),
                    web_port=int(item.get("web_port", 0)),
                    app_type=item.get("app_type", "web"),
                    status=status,
                    created_at=float(item.get("created_at", 0) or time.time()),
                    started_at=item.get("started_at"),
                    finished_at=item.get("finished_at"),
                    total_nodes=int(item.get("total_nodes", 0)),
                    estimated_cost=float(item.get("estimated_cost", 0.0)),
                    nodes=item.get("nodes") or {},
                    model=item.get("model", ""),
                    designer_model=item.get("designer_model", ""),
                    test_model=item.get("test_model", ""),
                    developer_model=item.get("developer_model", ""),
                )
                record.logs.extend(item.get("logs") or [])
                if status == TaskStatus.FAILED and "重启" not in str(item.get("logs", [])):
                    record.logs.append(
                        {"timestamp": _now_str(), "level": "ERROR",
                         "message": "服务重启导致编译进程终止，任务已标记为失败"}
                    )
                self._tasks[record.task_id] = record
                if record.web_port >= self._next_port:
                    self._next_port = record.web_port + 1
            except Exception:  # noqa: BLE001 - skip corrupted entries
                continue


# Module-level singleton accessor.
_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    global _manager
    if _manager is None:
        _manager = TaskManager()
    return _manager
