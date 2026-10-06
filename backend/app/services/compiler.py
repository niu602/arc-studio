"""Wrapper around the external ARC compiler.

The compiler is a long-running CLI driven through its own virtualenv. We launch
it with ``subprocess.Popen``, stream stdout/stderr line-by-line into the task
log, and heuristically parse node-id / status / stage changes out of the text.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional

from app import config
from app.models import NodeStatus, Stage
from app.services.task_manager import TaskManager, TaskRecord, get_task_manager

# Node ids look like REQ-1, REQ-1-2, ROOT, ...
_NODE_ID_RE = re.compile(r"\b(?:REQ|ROOT)-\d+(?:-\d+)*\b")


def _classify_level(line: str) -> str:
    lower = line.lower()
    if any(k in lower for k in ("error", "failed", "exception", "traceback", "✗")):
        return "ERROR"
    if any(k in lower for k in ("✓", "passed", "success", "completed", "done")):
        return "SUCCESS"
    if any(k in lower for k in ("warn", "warning")):
        return "WARNING"
    return "INFO"


def _detect_stage(line: str) -> Optional[Stage]:
    if re.search(r"\b(design|designing)\b", line, re.IGNORECASE):
        return Stage.DESIGN
    if re.search(r"\b(implement|implementing|coding|development)\b", line, re.IGNORECASE):
        return Stage.IMPLEMENT
    if re.search(r"\b(test|testing)\b", line, re.IGNORECASE):
        return Stage.TEST
    return None


def _parse_and_update(tm: TaskManager, record: TaskRecord, line: str) -> None:
    node_ids = _NODE_ID_RE.findall(line)
    if not node_ids:
        return

    stage = _detect_stage(line)
    level = _classify_level(line)
    for node_id in node_ids:
        if level == "SUCCESS":
            tm.update_node(record, node_id, status=NodeStatus.PASSED, stage=stage)
        elif level == "ERROR":
            tm.update_node(record, node_id, status=NodeStatus.FAILED, stage=stage)
        elif stage is not None:
            tm.update_node(record, node_id, status=NodeStatus.RUNNING, stage=stage)
        else:
            # First time we see a node: mark it running in its current stage.
            tm.update_node(record, node_id, status=NodeStatus.RUNNING)


class CompilerService:
    def __init__(self) -> None:
        self.tm: TaskManager = get_task_manager()

    # ------------------------------------------------------------------
    def build_env(self, record: TaskRecord) -> dict[str, str]:
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = record.api_key
        env["OPENAI_BASE_URL"] = record.base_url

        # Per-stage models the ARC compiler reads from the environment.
        designer = record.designer_model or config.DEFAULT_DESIGNER_MODEL
        tester = record.test_model or config.DEFAULT_TEST_MODEL
        developer = record.developer_model or config.DEFAULT_DEVELOPER_MODEL
        env["ARC_MODEL_INTERFACE_DESIGNER"] = designer
        env["ARC_MODEL_TEST_GENERATOR"] = tester
        env["ARC_MODEL_TEST_DRIVEN_DEVELOPER"] = developer
        # Legacy single-MODEL compatibility: default to the designer model.
        env["MODEL"] = record.model or designer

        env["ARC_OPENAI_API_MODE"] = config.ARC_OPENAI_API_MODE
        # Ensure child python prints UTF-8 (main.py already reconfigures streams,
        # but belt-and-suspenders on Windows).
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def build_command(self, record: TaskRecord) -> list[str]:
        return [
            config.COMPILER_PYTHON,
            config.COMPILER_MAIN,
            "compile",
            str(record.requirement_path),
            "-o",
            str(record.output_dir),
            "-t",
            record.app_type,
            "--port",
            str(record.web_port),
        ]

    # ------------------------------------------------------------------
    def run_compilation(self, record: TaskRecord) -> None:
        """Entry point executed on a background thread."""
        from app.models import TaskStatus

        tm = self.tm
        tm.set_status(record, TaskStatus.RUNNING)
        command = self.build_command(record)
        env = self.build_env(record)

        tm.append_log(record, "INFO", f"启动编译器: {' '.join(command)}")
        tm.append_log(record, "INFO", f"需求文件: {record.requirement_path}")
        tm.append_log(record, "INFO", f"输出目录: {record.output_dir}")
        tm.append_log(record, "INFO", f"应用类型: {record.app_type} | Web 预览端口: {record.web_port}")
        tm.append_log(record, "INFO", f"模型 -> 设计: {env['ARC_MODEL_INTERFACE_DESIGNER']} | "
                                      f"测试: {env['ARC_MODEL_TEST_GENERATOR']} | "
                                      f"开发: {env['ARC_MODEL_TEST_DRIVEN_DEVELOPER']}")

        cwd = str(Path(config.COMPILER_MAIN).resolve().parent)
        try:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except Exception as exc:  # noqa: BLE001 - surface to task log
            from app.models import TaskStatus

            tm.append_log(record, "ERROR", f"无法启动编译器进程: {exc}")
            tm.set_status(record, TaskStatus.FAILED)
            return

        record.process = proc

        # Stream stdout in this thread (we are already on a worker thread).
        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                line = raw.rstrip()
                if not line:
                    continue
                tm.append_log(record, _classify_level(line), line)
                _parse_and_update(tm, record, line)
        except Exception as exc:  # noqa: BLE001
            tm.append_log(record, "ERROR", f"读取编译器输出异常: {exc}")
        finally:
            proc.wait()
            exit_code = proc.returncode
            record.process = None

        from app.models import TaskStatus  # local import to avoid cycle at module load

        if record.status == TaskStatus.CANCELLED:
            tm.append_log(record, "WARNING", f"编译任务已被用户取消 (exit={exit_code})")
            self.stop_preview(record)
        elif exit_code == 0:
            tm.append_log(record, "SUCCESS", "编译器执行完成，exit=0")
            tm.set_status(record, TaskStatus.COMPLETED)
            self.start_preview(record)
        else:
            tm.append_log(record, "ERROR", f"编译器异常退出，exit={exit_code}")
            tm.set_status(record, TaskStatus.FAILED)

    # ------------------------------------------------------------------
    def cancel(self, record: TaskRecord) -> str:
        from app.models import TaskStatus

        proc = record.process
        if proc is not None and record.status in (TaskStatus.RUNNING, TaskStatus.PENDING):
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as exc:  # noqa: BLE001
                return f"取消进程时出错: {exc}"
            self.tm.set_status(record, TaskStatus.CANCELLED)
            self.tm.append_log(record, "WARNING", "收到取消请求，已终止编译器进程")

        # Always stop any preview server, even if the compile already finished.
        self.stop_preview(record)
        return f"任务 {record.task_id} 已取消"

    # ------------------------------------------------------------------
    # Preview server management
    # ------------------------------------------------------------------
    @staticmethod
    def _find_package_json(output_dir: Path) -> Optional[Path]:
        """Locate the generated app's package.json (root or one level deep)."""
        candidates = [output_dir / "package.json"]
        for sub in ("web", "frontend", "app", "client"):
            candidates.append(output_dir / sub / "package.json")
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        # Fall back to the first package.json under output_dir.
        found = list(output_dir.rglob("package.json"))
        # Skip node_modules copies.
        for f in found:
            if "node_modules" not in f.parts:
                return f
        return None

    def start_preview(self, record: TaskRecord) -> None:
        """Start the generated app so the frontend can embed a live preview."""
        tm = self.tm
        if record.app_type != "web":
            tm.append_log(record, "INFO", f"应用类型 {record.app_type} 不启动 Web 预览服务")
            return

        pkg = self._find_package_json(record.output_dir)
        if pkg is None:
            tm.append_log(record, "WARNING", "未找到 package.json，跳过预览服务启动")
            return

        app_dir = pkg.parent
        port = record.web_port
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            if not (app_dir / "node_modules").exists():
                tm.append_log(record, "INFO", "安装前端依赖 (npm install --prefer-offline)...")
                subprocess.run(
                    ["npm", "install", "--prefer-offline"],
                    cwd=str(app_dir), env=env, timeout=600,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            proc = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", str(port), "--host"],
                cwd=str(app_dir), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
        except Exception as exc:  # noqa: BLE001
            tm.append_log(record, "WARNING", f"预览服务启动失败: {exc}")
            record.preview_process = None
            return

        record.preview_process = proc
        tm.append_log(record, "SUCCESS", f"预览服务已启动: http://localhost:{port}  (PID {proc.pid})")

    def stop_preview(self, record: TaskRecord) -> None:
        proc = record.preview_process
        if proc is None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception:  # noqa: BLE001
            pass
        record.preview_process = None
        self.tm.append_log(record, "INFO", "预览服务已停止")

    def start_in_background(self, record: TaskRecord) -> None:
        thread = threading.Thread(
            target=self.run_compilation,
            args=(record,),
            daemon=True,
            name=f"compile-{record.task_id}",
        )
        thread.start()
