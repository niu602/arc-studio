"""Tool-level guardrails for ARC's staged agent workflow."""

from __future__ import annotations

import json
import os
from typing import Any, Literal, NotRequired, TypedDict

from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage

_FILE_WRITE_TOOLS = frozenset({"edit_file", "write_file"})
_VALIDATION_TOOLS = frozenset({"run_build", "run_tests"})
_DISCOVERY_TOOLS = frozenset({"ls", "glob", "grep"})
_MAX_DESIGN_WRITES = 8
_MAX_SKELETON_LINES = 160
_MAX_READ_LIMIT = 200
_DEFAULT_DESIGN_MAX_TURNS = 40
_DEFAULT_IMPLEMENT_MAX_TURNS = 100
_DEFAULT_IMPLEMENT_DISCOVERY_LIMIT = 40


class StageDisciplineState(TypedDict, total=False):
    """Run-local state used to prevent redundant file-tool loops."""

    arc_read_summaries: NotRequired[dict[str, str]]
    arc_written_paths: NotRequired[list[str]]


class StageDisciplineMiddleware(AgentMiddleware[StageDisciplineState, Any, Any]):
    """Enforce stage boundaries and stop post-write self-review loops."""

    state_schema = StageDisciplineState

    def __init__(
        self,
        *,
        stage: Literal["interface_design", "test_generation", "implementation"],
        shared_discovery: dict[str, Any] | None = None,
    ) -> None:
        self._stage = stage
        self._read_ranges: dict[str, list[tuple[int, int]]] = {}
        self._written_paths: set[str] = set()
        self._failed_paths: set[str] = set()
        self._validation_failed = False
        self._design_write_count = 0
        self._discovery_queries: set[str] = set()
        self._shared_discovery = shared_discovery
        self._model_calls = 0
        self._discovery_count = 0
        self._discovery_limit = (
            max(0, int(os.environ.get("ARC_IMPLEMENT_DISCOVERY_LIMIT", str(_DEFAULT_IMPLEMENT_DISCOVERY_LIMIT))))
            if stage == "implementation"
            else 0
        )
        if stage == "interface_design":
            self._max_turns = max(
                0, int(os.environ.get("ARC_DESIGN_MAX_TURNS", str(_DEFAULT_DESIGN_MAX_TURNS)))
            )
        elif stage == "implementation":
            self._max_turns = max(
                0, int(os.environ.get("ARC_IMPLEMENT_MAX_TURNS", str(_DEFAULT_IMPLEMENT_MAX_TURNS)))
            )
        else:
            self._max_turns = 0

    def wrap_model_call(self, request: Any, handler: Any) -> Any:
        self._model_calls += 1
        if self._max_turns and self._model_calls > self._max_turns:
            raise RuntimeError(
                f"Stage {self._stage!r} exceeded the {self._max_turns}-turn limit for this node; "
                "aborting the stage to stop the loss."
            )
        return handler(request)

    async def awrap_model_call(self, request: Any, handler: Any) -> Any:
        self._model_calls += 1
        if self._max_turns and self._model_calls > self._max_turns:
            raise RuntimeError(
                f"Stage {self._stage!r} exceeded the {self._max_turns}-turn limit for this node; "
                "aborting the stage to stop the loss."
            )
        return await handler(request)

    def wrap_tool_call(self, request: ToolCallRequest, handler: Any) -> ToolMessage | Any:
        cached = self._cached_discovery_result(request)
        if cached is not None:
            return cached
        blocked = self._validate_tool_call(request)
        if blocked:
            return self._blocked(request, blocked)
        request = self._with_bounded_read(request)
        result = handler(request)
        self._record_result(request, result)
        return result

    async def awrap_tool_call(self, request: ToolCallRequest, handler: Any) -> ToolMessage | Any:
        cached = self._cached_discovery_result(request)
        if cached is not None:
            return cached
        blocked = self._validate_tool_call(request)
        if blocked:
            return self._blocked(request, blocked)
        request = self._with_bounded_read(request)
        result = await handler(request)
        self._record_result(request, result)
        return result

    def _validate_tool_call(self, request: ToolCallRequest) -> str | None:
        name = str(request.tool_call.get("name", ""))
        args = request.tool_call.get("args", {}) or {}
        if name in {"execute", "delete"}:
            return f"`{name}` is disabled in ARC's staged file workflow."
        if self._stage == "test_generation" and name in _VALIDATION_TOOLS:
            return "TestGenerator only creates tests and its manifest; it must not run validation."
        if name == "read_file":
            return self._validate_read(args)
        if name in _FILE_WRITE_TOOLS:
            return self._validate_write(args)
        if name in _DISCOVERY_TOOLS:
            scope_block = _validate_discovery_scope(name, args)
            if scope_block is not None:
                return scope_block
            key = _discovery_key(name, args)
            if key in self._discovery_queries:
                return f"Repeated discovery blocked: identical {name} already ran in this stage; reuse its result."
            if self._discovery_limit and self._discovery_count >= self._discovery_limit:
                return (
                    f"Discovery budget exhausted ({self._discovery_count}/{self._discovery_limit}). "
                    "Stop exploring; use the requirement/interface/test context already provided and proceed to edit and run_tests."
                )
            self._discovery_queries.add(key)
            self._discovery_count += 1
        return None

    def _cached_discovery_result(self, request: ToolCallRequest) -> ToolMessage | None:
        if self._shared_discovery is None:
            return None
        name = str(request.tool_call.get("name", ""))
        if name not in _DISCOVERY_TOOLS:
            return None
        args = request.tool_call.get("args", {}) or {}
        content = self._shared_discovery.get(_discovery_key(name, args))
        if content is None:
            return None
        return ToolMessage(
            content=content,
            name=name,
            tool_call_id=str(request.tool_call.get("id", "")),
            status="success",
        )

    def _validate_read(self, args: dict[str, Any]) -> str | None:
        path = _discipline_path(args)
        if not path:
            return None
        if path in self._written_paths and not self._path_unlocked(path):
            return (
                f"Read blocked: {path} was already written in this stage. Continue to the next action; "
                "re-read only after a file-operation or system-validation error."
            )
        offset = _as_nonnegative_int(args.get("offset"), default=0)
        limit = min(_as_nonnegative_int(args.get("limit"), default=100), _MAX_READ_LIMIT)
        previous = self._read_ranges.get(path, [])
        if not previous or self._path_unlocked(path):
            return None
        if any(_ranges_overlap(offset, offset + limit, start, end) for start, end in previous):
            return (
                f"Repeated read blocked: {path} is already in this stage's read cache. "
                "Use the earlier result; only a non-overlapping paginated range or a failure may justify another read."
            )
        return None

    def _validate_write(self, args: dict[str, Any]) -> str | None:
        path = _discipline_path(args)
        if not path:
            return None
        if path in self._written_paths and not self._path_unlocked(path):
            return (
                f"Repeated write blocked: {path} was already changed in this stage. "
                "Wait for a file-operation or system-validation error before changing it again."
            )
        if self._stage == "test_generation" and not _is_test_asset(path):
            return (
                "TestGenerator may write only test files, test helpers/configuration, and the returned manifest; "
                f"{path} is not a test asset."
            )
        if self._stage == "interface_design":
            if path not in self._written_paths and self._design_write_count >= _MAX_DESIGN_WRITES:
                return (
                    f"InterfaceDesigner may materialize at most {_MAX_DESIGN_WRITES} small skeleton files. "
                    "Record remaining interfaces in the response for TDD."
                )
            content = str(args.get("content", args.get("new_string", "")) or "")
            if content.count("\n") + 1 > _MAX_SKELETON_LINES:
                return (
                    f"InterfaceDesigner may only materialize small skeletons (at most {_MAX_SKELETON_LINES} lines per write). "
                    "Record the complete business contract for TDD instead of implementing it now."
                )
        return None

    def _with_bounded_read(self, request: ToolCallRequest) -> ToolCallRequest:
        if request.tool_call.get("name") != "read_file":
            return request
        args = dict(request.tool_call.get("args", {}) or {})
        if not _discipline_path(args).startswith("/workspace/"):
            return request
        args["offset"] = _as_nonnegative_int(args.get("offset"), default=0)
        args["limit"] = min(_as_nonnegative_int(args.get("limit"), default=100), _MAX_READ_LIMIT)
        return request.override(tool_call={**request.tool_call, "args": args})

    def _record_result(self, request: ToolCallRequest, result: ToolMessage | Any) -> None:
        name = str(request.tool_call.get("name", ""))
        args = request.tool_call.get("args", {}) or {}
        path = _discipline_path(args)
        if name in _VALIDATION_TOOLS:
            if _tool_result_failed(result):
                self._validation_failed = True
                self._failed_paths.update(self._written_paths)
            return
        if _tool_result_failed(result):
            if path:
                self._failed_paths.add(path)
            return
        if name in _DISCOVERY_TOOLS and self._shared_discovery is not None:
            key = _discovery_key(name, args)
            content = getattr(result, "content", "") or ""
            if content and key not in self._shared_discovery:
                self._shared_discovery[key] = content
        if name == "read_file" and path:
            offset = _as_nonnegative_int(args.get("offset"), default=0)
            limit = _as_nonnegative_int(args.get("limit"), default=100)
            self._read_ranges.setdefault(path, []).append((offset, offset + limit))
            self._cache_read_summary(request, path, offset, limit, result)
        if name in _FILE_WRITE_TOOLS and path:
            if path not in self._written_paths and self._stage == "interface_design":
                self._design_write_count += 1
            self._written_paths.add(path)
            self._cache_written_path(request, path)

    def _path_unlocked(self, path: str) -> bool:
        return self._validation_failed or path in self._failed_paths

    @staticmethod
    def _cache_read_summary(request: ToolCallRequest, path: str, offset: int, limit: int, result: ToolMessage | Any) -> None:
        if not isinstance(request.state, dict):
            return
        content = str(getattr(result, "content", "") or "")
        line_count = content.count("\n") + (1 if content else 0)
        request.state.setdefault("arc_read_summaries", {})[path] = (
            f"lines {offset}-{offset + limit - 1}; received {line_count} line(s), {len(content)} character(s)"
        )

    @staticmethod
    def _cache_written_path(request: ToolCallRequest, path: str) -> None:
        if isinstance(request.state, dict):
            written = request.state.setdefault("arc_written_paths", [])
            if path not in written:
                written.append(path)

    @staticmethod
    def _blocked(request: ToolCallRequest, message: str) -> ToolMessage:
        return ToolMessage(
            content=f"Error: ARC stage discipline: {message}",
            name=str(request.tool_call.get("name", "tool")),
            tool_call_id=str(request.tool_call.get("id", "")),
            status="error",
        )


def _validate_discovery_scope(name: str, args: dict[str, Any]) -> str | None:
    """Block filesystem-wide discovery (base path `/`, `.`, or unscoped `**`) that
    walks the entire virtual tree and hits the grep/glob internal timeouts."""
    if name not in ("grep", "glob"):
        return None
    base = str(args.get("path", "") or "").replace("\\", "/").strip()
    if base in ("/", "."):
        return (
            f"`{name}` with base path `{base}` walks the entire virtual filesystem and times out; "
            "use a concrete directory under /workspace (e.g. /workspace/frontend/src)."
        )
    if name == "glob" and not base:
        pattern = str(args.get("pattern", "") or "").strip()
        if pattern.startswith("**") or pattern == "*":
            return (
                f"`glob` pattern `{pattern}` is unscoped; add a concrete `path` or a non-root pattern "
                "to avoid walking the entire virtual tree."
            )
    return None


def _discovery_key(name: str, args: dict[str, Any]) -> str:
    return f"{name}:{json.dumps(args, sort_keys=True, default=str)}"


def _discipline_path(args: dict[str, Any]) -> str:
    raw = str(args.get("file_path", "") or "").replace("\\", "/").strip()
    return raw if raw.startswith("/") else f"/{raw}" if raw else ""


def _as_nonnegative_int(value: Any, *, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _ranges_overlap(start: int, end: int, other_start: int, other_end: int) -> bool:
    return start < other_end and other_start < end


def _tool_result_failed(result: ToolMessage | Any) -> bool:
    if isinstance(result, ToolMessage) and result.status == "error":
        return True
    content = str(getattr(result, "content", "") or "")
    return "Exit Code: 0" not in content and ("Exit Code:" in content or content.lstrip().startswith("Error:"))


def _is_test_asset(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    test_segments = ("/test/", "/tests/", "/__tests__/", "/e2e/", "/__mocks__/")
    test_names = (".test.", ".spec.", "playwright.config.", "vitest.config.", "jest.config.", "setup-tests.", "setuptests.")
    return any(segment in normalized for segment in test_segments) or any(marker in name for marker in test_names)
