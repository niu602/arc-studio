from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from app_type_handler import create_app_type_handler
from agents.context.pipeline import context_pipeline
from core import sessions
from core.service import get_runtime
from core.path_compat import normalize_windows_extended_prefix_text
from core.visual_analysis import analyze_and_attach_visual_references
from app_type_handler.test_results import parse_test_results


LogCallback = Callable[[str, str, str | None, str | None], Awaitable[None] | None]
TDD_RUN_TESTS_BUDGET = max(1, int(os.environ.get("ARC_TDD_RUN_TESTS_BUDGET", "7")))
ALLOWED_INTERFACE_TYPES = {"UI", "API", "FUNC", "DB"}
TDD_BATCH_ORDER = ("Unit", "Integration", "E2E")

# P1 方案3：分层预算（从 v7 实测数据反推：Integration 是成本黑洞，Unit/E2E 用不完预算）
TDD_LAYER_BUDGETS = {
    "Unit": max(1, int(os.environ.get("ARC_TDD_BUDGET_UNIT", "5"))),
    "Integration": max(1, int(os.environ.get("ARC_TDD_BUDGET_INTEGRATION", "3"))),
    "E2E": max(1, int(os.environ.get("ARC_TDD_BUDGET_E2E", "5"))),
}
# P1 方案3：同一层连续 N 次「相同 exit code + 相同错误摘要」即判该层失败，提前止损
TDD_CONSECUTIVE_FAIL_STOP = max(1, int(os.environ.get("ARC_TDD_CONSECUTIVE_FAIL_STOP", "3")))
# P1 方案4：预算耗尽且「接近通过」时用 fallback 模型升级重跑一次
TDD_FALLBACK_MODEL = os.environ.get("ARC_MODEL_TEST_DRIVEN_DEVELOPER_FALLBACK", "qwen3.7-plus").strip()
TDD_FALLBACK_BUDGET = max(1, int(os.environ.get("ARC_TDD_FALLBACK_BUDGET", "3")))
TDD_FALLBACK_MAX_FAILED_TESTS = max(0, int(os.environ.get("ARC_TDD_FALLBACK_MAX_FAILED_TESTS", "2")))

class WorkflowPhaseRunner:
    """Run ARC DESIGN and IMPLEMENT phases using the agent adapters."""

    def __init__(
        self,
        *,
        workspace_path: str,
        requirement_path: str,
        app_type: str,
        interface_designer: Any,
        test_generator: Any,
        test_driven_developer: Any,
        log_cb: LogCallback | None = None,
    ) -> None:
        self.workspace_path = str(Path(workspace_path).expanduser().resolve())
        self.requirement_path = requirement_path
        self.app_type = app_type
        self.interface_designer = interface_designer
        self.test_generator = test_generator
        self.test_driven_developer = test_driven_developer
        self.log_cb = log_cb
        self.app_handler = create_app_type_handler(
            app_type=app_type,
            workspace_path=self.workspace_path,
            requirement_path=requirement_path,
            interface_designer=interface_designer,
            log_cb=self._log,
        )
        self.test_driven_developer.app_handler = self.app_handler

    @property
    def traceability(self):
        return get_runtime().traceability

    @staticmethod
    def _is_shell_node(node_id: str) -> bool:
        """Return True when a non-leaf node is an explicit UI shell that owns
        visual/composition boundaries and should still run a thin UI-only DESIGN.

        Aggregation FOLDER nodes are skipped by default; opt a node back in by
        listing it in ARC_DESIGN_SHELL_NODE_IDS (comma-separated)."""
        shell_ids = {
            value.strip()
            for value in os.environ.get("ARC_DESIGN_SHELL_NODE_IDS", "REQ-1,REQ-2,REQ-3,REQ-4,REQ-5,REQ-6").split(",")
            if value.strip()
        }
        return node_id in shell_ids

    async def run_design_phase(self, node_id: str, requirement_data: dict[str, Any]) -> bool:
        is_non_leaf = bool(requirement_data.get("children_ids"))
        requirement_data = await analyze_and_attach_visual_references(
            workspace_path=self.workspace_path,
            requirements_dir=str(Path(self.requirement_path).expanduser().resolve().parent),
            requirement_data=requirement_data,
            log_cb=self._log,
        )
        requirement_data = self.traceability.get_requirement(node_id) or requirement_data
        self._update_node_session(
            node_id,
            {
                "node_id": node_id,
                "phase_status": {"design": "pending", "test": "pending", "implement": "pending"},
                "requirement_snapshot": {
                    "name": requirement_data.get("name", ""),
                    "description": requirement_data.get("description", ""),
                    "visual_reference": requirement_data.get("visual_reference") or [],
                    "children_ids": requirement_data.get("children_ids") or [],
                    "dependencies": requirement_data.get("dependencies") or [],
                },
                "recent_failure_summary": "",
            },
        )

        if is_non_leaf and not self._is_shell_node(node_id):
            self.traceability.clear_node_design_artifacts(node_id)
            context_pipeline.cache.invalidate_file_layers(node_id)
            context_pipeline.cache.invalidate_db_layers(node_id)
            self._update_node_session(
                node_id,
                {
                    "interfaces": [],
                    "materialized_files": [],
                    "test_artifacts": [],
                    "phase_status": {"design": "skipped", "test": "skipped"},
                },
            )
            await self._log(
                "InterfaceDesigner",
                "Skipping non-leaf DESIGN for aggregation node; visual analysis stays inherited by children and no UI/API/FUNC/DB interfaces are owned here.",
                status="info",
                node_id=node_id,
            )
            await self._log(
                "TestGenerator",
                "Skipping test generation for non-leaf node.",
                status="info",
                node_id=node_id,
            )
            return True

        await self._log("InterfaceDesigner", "Running interface design.", node_id=node_id)
        interface_result = await self.interface_designer.run(
            node_id=node_id,
            requirement_data=requirement_data,
        )
        interfaces = []
        for item in interface_result.get("interfaces", []):
            if not isinstance(item, dict):
                continue
            normalized = dict(item)
            normalized["file_path"] = normalize_workspace_relative_path(normalized.get("file_path"), self.workspace_path)
            interfaces.append(normalized)
        files_written = []
        for path in interface_result.get("files_written") or []:
            normalized_path = normalize_workspace_relative_path(path, self.workspace_path)
            if normalized_path:
                files_written.append(normalized_path)
        if not interfaces:
            await self._log(
                "InterfaceDesigner",
                "Interface design returned no current-node owned interface definitions.",
                status="warning",
                node_id=node_id,
            )

        try:
            prepared_interfaces = self._prepare_interfaces(node_id, interfaces)
        except ValueError as exc:
            await self._log("InterfaceDesigner", str(exc), status="error", node_id=node_id)
            return False
        context_pipeline.cache.invalidate_file_layers(node_id)
        context_pipeline.cache.invalidate_db_layers(node_id)
        self._update_node_session(
            node_id,
            {
                "interfaces": prepared_interfaces,
                "materialized_files": files_written,
                "phase_status": {"design": "prepared"},
            },
        )
        context_pipeline.cache.invalidate_db_layers(node_id)

        stored_tests: list[dict[str, Any]] = []
        if is_non_leaf:
            self.traceability.clear_node_design_artifacts(node_id)
            self._store_prepared_interfaces(node_id, prepared_interfaces)
            context_pipeline.cache.invalidate_file_layers(node_id)
            context_pipeline.cache.invalidate_db_layers(node_id)
            self._update_node_session(
                node_id,
                {
                    "interfaces": prepared_interfaces,
                    "test_artifacts": [],
                    "phase_status": {"design": "completed", "test": "skipped"},
                },
            )
            await self._log(
                "InterfaceDesigner",
                f"Stored {len(prepared_interfaces)} interface definition(s) into traceability DB.",
                node_id=node_id,
            )
            await self._log(
                "InterfaceDesigner",
                f"Interface artifact summary: {json.dumps(summarize_interface_artifacts(prepared_interfaces), ensure_ascii=False)}",
                node_id=node_id,
            )
            await self._log(
                "TestGenerator",
                "Skipping test generation for non-leaf node; composition nodes only define interfaces.",
                status="info",
                node_id=node_id,
            )
            return True

        await self._log(
            "InterfaceDesigner",
            f"Prepared {len(prepared_interfaces)} interface definition(s) for traceability storage.",
            node_id=node_id,
        )
        await self._log(
            "InterfaceDesigner",
            f"Interface artifact summary: {json.dumps(summarize_interface_artifacts(prepared_interfaces), ensure_ascii=False)}",
            node_id=node_id,
        )

        await self._log("TestGenerator", "Generating tests from agent-selected coverage strategy.", node_id=node_id)
        tests, _ = await self.test_generator.run(
            node_id=node_id,
            requirement_data=requirement_data,
        )
        if tests is None:
            await self._log(
                "TestGenerator",
                "DESIGN test generation did not return a valid test manifest.",
                status="error",
                node_id=node_id,
            )
            return False

        try:
            stored_tests = self._prepare_tests(node_id=node_id, tests=tests)
        except ValueError as exc:
            await self._log("TestGenerator", str(exc), status="error", node_id=node_id)
            return False

        self.traceability.clear_node_design_artifacts(node_id)
        self._store_prepared_interfaces(node_id, prepared_interfaces)
        self._store_prepared_tests(stored_tests)
        context_pipeline.cache.invalidate_file_layers(node_id)
        context_pipeline.cache.invalidate_db_layers(node_id)
        self._update_node_session(
            node_id,
            {
                "interfaces": prepared_interfaces,
                "test_artifacts": stored_tests,
                "phase_status": {"design": "completed", "test": "completed"},
            },
        )
        await self._log(
            "InterfaceDesigner",
            f"Stored {len(prepared_interfaces)} interface definition(s) into traceability DB.",
            node_id=node_id,
        )
        await self._log(
            "TestGenerator",
            f"Stored {len(stored_tests)} test mapping item(s) into traceability DB.",
            node_id=node_id,
        )
        await self._log(
            "TestGenerator",
            f"Test artifact summary: {json.dumps(summarize_test_artifacts(stored_tests), ensure_ascii=False)}",
            node_id=node_id,
        )
        return True

    async def run_test_generation_phase(
        self,
        node_id: str,
        requirement_data: dict[str, Any],
        *,
        intent: str,
        replace_test_id: str | None = None,
    ) -> bool:
        normalized_intent = str(intent or "").strip()
        if not normalized_intent:
            await self._log("TestGenerator", "A test intent is required.", status="error", node_id=node_id)
            return False
        if requirement_data.get("children_ids"):
            await self._log(
                "TestGenerator",
                "Intent-based test generation is only available for leaf requirement nodes.",
                status="error",
                node_id=node_id,
            )
            return False

        normalized_replace_test_id = str(replace_test_id or "").strip()
        existing_tests = self.traceability.list_tests(req_id=node_id)
        existing_by_id = {
            str(test.get("test_id", "") or "").strip(): test
            for test in existing_tests
            if str(test.get("test_id", "") or "").strip()
        }
        existing_test = existing_by_id.get(normalized_replace_test_id)
        if normalized_replace_test_id and existing_test is None:
            await self._log(
                "TestGenerator",
                f"Test regeneration received unregistered test id: {normalized_replace_test_id}",
                status="error",
                node_id=node_id,
            )
            return False
        action = f"Regenerating test {normalized_replace_test_id}" if normalized_replace_test_id else "Adding tests"
        await self._log("TestGenerator", f"{action} for intent: {normalized_intent}", node_id=node_id)
        tests, _ = await self.test_generator.run(
            node_id=node_id,
            requirement_data=requirement_data,
            test_intent=normalized_intent,
            replace_test_id=normalized_replace_test_id or None,
        )
        if tests is None:
            await self._log("TestGenerator", "Test generation did not return a valid manifest.", status="error", node_id=node_id)
            return False
        try:
            prepared_tests = self._prepare_tests(node_id=node_id, tests=tests)
        except ValueError as exc:
            await self._log("TestGenerator", str(exc), status="error", node_id=node_id)
            return False

        existing_ids = set(existing_by_id)
        if normalized_replace_test_id:
            generated_ids = {str(test.get("test_id", "") or "").strip() for test in prepared_tests}
            if generated_ids != {normalized_replace_test_id}:
                await self._log(
                    "TestGenerator",
                    f"Test regeneration must return only the selected test id: {normalized_replace_test_id}",
                    status="error",
                    node_id=node_id,
                )
                return False
            original_path = str(existing_test.get("file_path", "") or "").strip()
            generated_path = str(prepared_tests[0].get("file_path", "") or "").strip() if prepared_tests else ""
            if original_path != generated_path:
                await self._log(
                    "TestGenerator",
                    f"Test regeneration must preserve the selected test file path: {original_path}",
                    status="error",
                    node_id=node_id,
                )
                return False
        duplicate_ids = sorted(
            test_id
            for test_id in (str(test.get("test_id", "") or "").strip() for test in prepared_tests)
            if test_id in existing_ids and test_id != normalized_replace_test_id
        )
        if duplicate_ids:
            await self._log(
                "TestGenerator",
                f"Test generation would overwrite existing test id(s): {', '.join(duplicate_ids)}",
                status="error",
                node_id=node_id,
            )
            return False

        self._store_prepared_tests(prepared_tests)
        context_pipeline.cache.invalidate_file_layers(node_id)
        context_pipeline.cache.invalidate_db_layers(node_id)
        await self._log(
            "TestGenerator",
            f"Stored {len(prepared_tests)} test mapping item(s) for the requested generation.",
            node_id=node_id,
        )
        return True

    async def run_implement_phase(
        self,
        node_id: str,
        requirement_data: dict[str, Any],
        test_ids: list[str] | None = None,
    ) -> bool:
        is_non_leaf = bool(requirement_data.get("children_ids"))
        selected_test_ids = list(dict.fromkeys(str(test_id or "").strip() for test_id in test_ids or [] if str(test_id or "").strip()))
        if selected_test_ids and is_non_leaf:
            await self._log(
                "TestDrivenDeveloper",
                "Selected-test TDD is only available for leaf requirement nodes.",
                status="error",
                node_id=node_id,
            )
            return False
        if is_non_leaf:
            interfaces = self.traceability.list_interfaces(req_id=node_id)
            self._mark_interfaces_implemented(interfaces)
            self._update_node_session(
                node_id,
                {
                    "phase_status": {"implement": "completed"},
                    "result_state": "CONVERGED",
                },
            )
            await self._log(
                "TestDrivenDeveloper",
                "Non-leaf node completed directly after interface materialization; no TDD batch was scheduled.",
                node_id=node_id,
            )
            return True

        del requirement_data
        if not selected_test_ids:
            self._update_node_session(node_id, {"phase_status": {"implement": "in_progress"}})
        interfaces = self.traceability.list_interfaces(req_id=node_id)
        tests = self.traceability.list_tests(req_id=node_id)
        if selected_test_ids:
            tests_by_id = {
                str(test.get("test_id", "") or "").strip(): test
                for test in tests
                if str(test.get("test_id", "") or "").strip()
            }
            unknown_test_ids = [test_id for test_id in selected_test_ids if test_id not in tests_by_id]
            if unknown_test_ids:
                await self._log(
                    "TestDrivenDeveloper",
                    f"Selected-test TDD received unregistered test id(s): {', '.join(unknown_test_ids)}",
                    status="error",
                    node_id=node_id,
                )
                return False
            tests = [tests_by_id[test_id] for test_id in selected_test_ids]
        if not tests:
            await self._log(
                "TestDrivenDeveloper",
                "No node-local tests were registered; skipping TDD implementation for this node.",
                node_id=node_id,
            )
            if not selected_test_ids:
                self._mark_interfaces_implemented(interfaces)
                self._update_node_session(node_id, {"phase_status": {"implement": "completed"}})
            return True

        final_ok = await self._run_tdd_for_node(
            node_id=node_id,
            tests=tests,
        )
        if final_ok and not selected_test_ids:
            self._mark_interfaces_implemented(interfaces)
        if not selected_test_ids:
            self._update_node_session(
                node_id,
                {"phase_status": {"implement": "completed" if final_ok else "failed"}},
            )
        return final_ok

    async def _run_tdd_for_node(
        self,
        *,
        node_id: str,
        tests: list[dict[str, Any]],
    ) -> bool:
        previous_failure_summary = str(sessions.load_node_session(node_id).get("recent_failure_summary", "") or "")
        groups: dict[str, list[dict[str, Any]]] = {}
        for test in tests:
            test_type = str(test.get("type", "") or "").strip()
            if not test_type:
                continue
            normalized_type = test_type.lower()
            groups.setdefault(normalized_type, []).append(test)

        ordered_types = [test_type for test_type in TDD_BATCH_ORDER if groups.get(test_type.lower())]
        if not ordered_types:
            return True

        usage_by_type = {test_type: 0 for test_type in ordered_types}
        fallback_usage_by_type = {test_type: 0 for test_type in ordered_types}
        result_by_type: dict[str, str] = {}
        fallback_used: set[str] = set()
        consecutive_stop: set[str] = set()
        consecutive_fingerprints: dict[str, list[str]] = {test_type: [] for test_type in ordered_types}
        await self._log(
            "TestDrivenDeveloper",
            "Running leaf TDD sessions in ordered layers with independent budgets: " + " -> ".join(ordered_types) + ".",
            node_id=node_id,
        )
        active_test_type: str | None = None
        active_budget = TDD_RUN_TESTS_BUDGET
        active_is_fallback = False

        async def run_requested_tests(requested_type: str | None = None, requested_files: list[str] | None = None) -> str:
            requested = str(requested_type or "").strip()
            if active_test_type is None:
                return (
                    "Exit Code: 1\n"
                    "STDERR:\n"
                    "No active TDD test layer is currently scheduled.\n"
                )
            if requested.lower() in {"", "all", "current", "next"}:
                selected_type = active_test_type
            else:
                selected_type = canonical_test_type(requested)
                if selected_type is None or selected_type not in ordered_types:
                    return (
                        "Exit Code: 1\n"
                        "STDERR:\n"
                        f"Unsupported current-node test_type={requested!r}. "
                        f"Available ordered layers: {', '.join(ordered_types)}.\n"
                    )
                if selected_type != active_test_type:
                    return (
                        "Exit Code: 1\n"
                        "STDERR:\n"
                        f"The active TDD layer is `{active_test_type}`, but run_tests requested `{selected_type}`. "
                        "The system attempts layers in Unit -> Integration -> E2E order with independent budgets.\n"
                    )

            selected_files = [
                path
                for value in (requested_files or collect_test_files(groups[selected_type.lower()]))
                if (path := normalize_workspace_relative_path(value, self.workspace_path))
            ]
            registered_files = {
                str(item.get("file_path", "") or "").strip()
                for item in groups[selected_type.lower()]
                if str(item.get("file_path", "") or "").strip()
            }
            unknown = [path for path in selected_files if path not in registered_files]
            if unknown:
                return (
                    "Exit Code: 1\n"
                    "STDERR:\n"
                    f"run_tests({selected_type}) may only execute registered {selected_type} tests for the current node. "
                    f"Unknown files: {', '.join(unknown)}\n"
                )
            # Fix C: 如果本层已经通过，模型又调 run_tests()，直接返回"该层已过"，不消耗预算
            if parse_test_results(result_by_type.get(selected_type, "")).get("exit_code") == 0:
                return (
                    "Exit Code: 0\n"
                    f"STDERR:\n{selected_type} already passed. End your turn to advance to the next layer; "
                    "do not call run_tests again in this turn.\n"
                )
            current_usage = (
                fallback_usage_by_type if active_is_fallback else usage_by_type
            )
            current_budget = active_budget
            used = current_usage[selected_type]
            if used >= current_budget:
                await self._log(
                    "TestDrivenDeveloper",
                    f"`run_tests` {selected_type} budget exhausted at {used}/{current_budget}.",
                    status="error",
                    node_id=node_id,
                )
                return (
                    "Exit Code: 1\n"
                    "STDERR:\n"
                    f"run_tests budget exhausted for {selected_type}: {used}/{current_budget}.\n"
                )
            current_usage[selected_type] = used + 1
            await self._log(
                "TestDrivenDeveloper",
                f"`run_tests` {selected_type} usage {current_usage[selected_type]}/{current_budget}.",
                node_id=node_id,
            )
            output = await self.app_handler.run_test_group(selected_type, selected_files)
            await self._log(
                "TestDrivenDeveloper",
                (
                    "run_tests raw output\n"
                    f"test_type={selected_type}\n"
                    f"attempt={current_usage[selected_type]}/{current_budget}\n"
                    f"test_files={json.dumps(selected_files, ensure_ascii=False)}\n"
                    "----- BEGIN RAW TEST OUTPUT -----\n"
                    f"{output.rstrip()}\n"
                    "----- END RAW TEST OUTPUT -----"
                ),
                status="debug",
                node_id=node_id,
            )
            parsed_result = parse_test_results(output)
            exit_code = int(parsed_result.get("exit_code", -1))
            passed = exit_code == 0
            await self._log(
                "TestDrivenDeveloper",
                (
                    f"`run_tests` {selected_type} {'passed' if passed else 'failed'} "
                    f"with Exit Code: {exit_code} "
                    f"on attempt {current_usage[selected_type]}/{current_budget}: "
                    f"{', '.join(selected_files)}"
                ),
                status="ok" if passed else "error",
                node_id=node_id,
            )
            result_by_type[selected_type] = output
            if not passed and not active_is_fallback:
                self._record_consecutive_failure(
                    selected_type,
                    output,
                    consecutive_fingerprints,
                    consecutive_stop,
                )
                if selected_type in consecutive_stop:
                    await self._log(
                        "TestDrivenDeveloper",
                        f"`run_tests` {selected_type} hit {TDD_CONSECUTIVE_FAIL_STOP} consecutive identical failures; stopping this layer early.",
                        status="error",
                        node_id=node_id,
                    )
                    return (
                        "Exit Code: 1\n"
                        "STDERR:\n"
                        f"Consecutive identical failures detected for {selected_type}; this layer is stopped.\n"
                    )
            next_index = ordered_types.index(selected_type) + 1
            next_type = ordered_types[next_index] if next_index < len(ordered_types) else None
            if passed and next_type:
                output += (
                    "\n\nARC_TEST_LAYER_STATUS:\n"
                    f"- {selected_type} passed.\n"
                    f"- This layer is complete. The next layer ({next_type}) starts in a NEW turn.\n"
                    "- END this turn now: return a one-line status. Do NOT return IMPLEMENTED, and do NOT call run_tests again.\n"
                )
            elif passed:
                output += (
                    "\n\nARC_TEST_LAYER_STATUS:\n"
                    f"- {selected_type} passed.\n"
                    "- This was the last scheduled layer. You may now return exactly IMPLEMENTED.\n"
                )
            return output

        output = ""
        session_count = 0
        max_sessions = max(1, TDD_RUN_TESTS_BUDGET * len(ordered_types))
        for ordered_type in ordered_types:
            active_test_type = ordered_type
            layer_budget = TDD_LAYER_BUDGETS.get(ordered_type, TDD_RUN_TESTS_BUDGET)
            active_budget = layer_budget
            active_is_fallback = False
            previous_failure_summary = str(sessions.load_node_session(node_id).get("recent_failure_summary", "") or "")
            while parse_test_results(result_by_type.get(ordered_type, "")).get("exit_code") != 0:
                current_usage_map = fallback_usage_by_type if active_is_fallback else usage_by_type
                used_before = current_usage_map.get(ordered_type, 0)
                if used_before >= active_budget:
                    # 预算耗尽：仅在尚未升级、且"接近通过"时尝试 fallback 模型
                    if not active_is_fallback and self._should_escalate(result_by_type.get(ordered_type, "")):
                        active_is_fallback = True
                        active_budget = TDD_FALLBACK_BUDGET
                        fallback_used.add(ordered_type)
                        await self._log(
                            "TestDrivenDeveloper",
                            (
                                f"Escalating `{ordered_type}` to fallback model {TDD_FALLBACK_MODEL!r} "
                                f"after {used_before}/{layer_budget} run_tests call(s); retrying once with "
                                f"budget {TDD_FALLBACK_BUDGET}."
                            ),
                            status="warning",
                            node_id=node_id,
                        )
                        continue
                    break
                if ordered_type in consecutive_stop:
                    break
                if session_count >= max_sessions:
                    await self._log(
                        "TestDrivenDeveloper",
                        f"TDD stopped after {session_count} agent session(s); continuing layer summary with collected results.",
                        status="error",
                        node_id=node_id,
                    )
                    break

                session_count += 1
                if used_before > 0:
                    await self._log(
                        "TestDrivenDeveloper",
                        (
                            f"Resuming TDD agent session {session_count} for `{ordered_type}`; "
                            f"run_tests usage is {used_before}/{active_budget}."
                        ),
                        node_id=node_id,
                    )
                output = await self.test_driven_developer.run(
                    node_id=node_id,
                    test_files=collect_test_files(tests),
                    test_type=ordered_type,
                    node_tests=tests,
                    previous_failure_summary=previous_failure_summary,
                    run_tests_budget=None,
                    run_tests_usage=None,
                    run_tests_executor=run_requested_tests,
                    model=TDD_FALLBACK_MODEL if active_is_fallback else None,
                    thread_id_suffix=":fallback" if active_is_fallback else "",
                )

                latest_result = result_by_type.get(ordered_type, "")
                previous_failure_summary = (
                    self.test_driven_developer.get_last_verifier_report()
                    or summarize_batch_output(latest_result or output)
                )
                used_after = current_usage_map.get(ordered_type, 0)
                if parse_test_results(latest_result).get("exit_code") == 0:
                    break
                if used_after >= active_budget:
                    break
                if used_after == used_before:
                    await self._log(
                        "TestDrivenDeveloper",
                        (
                            f"TDD agent session ended without calling run_tests for `{ordered_type}`; "
                            "moving to the next scheduled layer with a fresh budget."
                        ),
                        status="error",
                        node_id=node_id,
                    )
                    break
            active_test_type = None
            active_is_fallback = False
            if parse_test_results(result_by_type.get(ordered_type, "")).get("exit_code") != 0:
                await self._log(
                    "TestDrivenDeveloper",
                    f"Advancing past `{ordered_type}` without a passing result; the next scheduled layer will start with its own budget.",
                    status="warning",
                    node_id=node_id,
                )

        final_ok = True
        failure_summaries: list[str] = []
        failed_types: list[str] = []
        for test_type in ordered_types:
            latest_result = result_by_type.get(test_type, "")
            group_passed = parse_test_results(latest_result).get("exit_code") == 0
            status_by_test_id = {
                str(test.get("test_id", "")).strip(): group_passed
                for test in groups[test_type.lower()]
                if str(test.get("test_id", "")).strip()
            }
            self.traceability.set_test_pass_statuses(status_by_test_id)
            layer_budget = TDD_LAYER_BUDGETS.get(test_type, TDD_RUN_TESTS_BUDGET)
            total_used = usage_by_type.get(test_type, 0) + fallback_usage_by_type.get(test_type, 0)
            if group_passed:
                await self._log(
                    "TestDrivenDeveloper",
                    f"TDD batch `{test_type}` passed after {total_used}/{layer_budget} run_tests call(s).",
                    node_id=node_id,
                )
                continue
            final_ok = False
            failed_types.append(test_type)
            failure_summary = (
                summarize_batch_output(latest_result)
                if latest_result
                else self.test_driven_developer.get_last_verifier_report()
                or summarize_batch_output(output)
            )
            failure_summaries.append(f"{test_type}: {failure_summary}")
            used = total_used
            detail = (
                "budget exhausted"
                if used >= layer_budget
                else "agent session ended before this layer passed"
            )
            await self._log(
                "TestDrivenDeveloper",
                f"TDD batch `{test_type}` did not pass after {used}/{layer_budget} run_tests call(s); {detail}.",
                status="error",
                node_id=node_id,
            )

        context_pipeline.cache.invalidate_db_layers(node_id)
        context_pipeline.cache.invalidate_file_layers(node_id)
        failure_summary = "\n\n".join(failure_summaries)
        self._update_node_session(
            node_id,
            {
                "recent_failure_summary": failure_summary,
                "tdd_handoff": {
                    "last_test_type": failed_types[-1] if failed_types else ordered_types[-1],
                    "last_failed_output_summary": failure_summary,
                    "modified_files": [],
                },
            },
        )
        if not final_ok:
            return False

        unexpected_types = sorted(set(groups) - {item.lower() for item in TDD_BATCH_ORDER})
        if unexpected_types:
            await self._log(
                "TestDrivenDeveloper",
                f"Ignoring unsupported test batch type(s): {', '.join(unexpected_types)}.",
                status="warning",
                node_id=node_id,
            )

        return True

    def _prepare_interfaces(self, node_id: str, interfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared: list[dict[str, Any]] = []
        for interface in interfaces:
            interface_id = str(interface.get("interface_id", "")).strip()
            if not interface_id:
                continue
            existing = self.traceability.get_interface(interface_id)
            if existing:
                try:
                    existing_content = json.loads(str(existing.get("content") or "{}"))
                except json.JSONDecodeError:
                    existing_content = {}
                if isinstance(existing_content, dict):
                    interface = {**existing_content, **interface}
            interface_type = str(interface.get("type") or (existing or {}).get("type") or "").strip().upper()
            if interface_type not in ALLOWED_INTERFACE_TYPES:
                raise ValueError(
                    f"Generated interface `{interface_id}` has invalid `type` {interface.get('type')!r}. "
                    "Interface type must be one of UI, API, FUNC, or DB."
                )
            normalized = {
                **interface,
                "interface_id": interface_id,
                "req_id": node_id,
                "type": interface_type,
                "file_path": (
                    normalize_workspace_relative_path(interface.get("file_path"), self.workspace_path)
                    or ((existing or {}).get("file_path") if existing else "")
                ),
                "first_line": str(interface.get("first_line") or (existing or {}).get("first_line") or "").strip(),
                "callers": normalize_string_list(interface.get("callers")) or normalize_string_list((existing or {}).get("callers")),
                "callees": normalize_string_list(interface.get("callees")) or normalize_string_list((existing or {}).get("callees")),
                "_existing_req_ids": list(existing.get("req_ids", [])) if existing else [],
                "_existing_implemented": bool(existing.get("implemented")) if existing else False,
            }
            prepared.append(normalized)
        return prepared

    def _store_prepared_interfaces(self, node_id: str, interfaces: list[dict[str, Any]]) -> None:
        for interface in interfaces:
            interface_id = str(interface.get("interface_id", "")).strip()
            if not interface_id:
                continue
            req_ids = normalize_string_list(interface.get("_existing_req_ids"))
            if node_id not in req_ids:
                req_ids.append(node_id)
            self.traceability.upsert_interface(
                interface_id=interface_id,
                req_ids=req_ids,
                type=str(interface.get("type", "") or "").strip().upper(),
                content=json.dumps(_strip_internal_fields(interface), ensure_ascii=False),
                file_path=str(interface.get("file_path", "") or "").strip() or None,
                first_line=str(interface.get("first_line", "") or "").strip() or None,
                implemented=bool(interface.get("_existing_implemented")),
                callers=normalize_string_list(interface.get("callers")),
                callees=normalize_string_list(interface.get("callees")),
            )
            self._register_interface_edges(node_id, interface_id, interface)

    def _prepare_tests(
        self,
        *,
        node_id: str,
        tests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        stored: list[dict[str, Any]] = []
        generated_ids: set[str] = set()
        for test in tests:
            if not isinstance(test, dict):
                continue
            raw_test_id = str(test.get("test_id", "")).strip()
            if not raw_test_id:
                continue
            file_path = normalize_workspace_relative_path(test.get("file_path"), self.workspace_path)
            test_type = str(test.get("type", "") or "").strip()
            if not test_type:
                raise ValueError(f"Generated test `{raw_test_id}` is missing `type`.")
            if not file_path:
                raise ValueError(f"Generated test `{raw_test_id}` is missing `file_path`.")
            validation_error = self.app_handler.validate_test_path(test_type, file_path)
            if validation_error:
                raise ValueError(f"Generated test `{raw_test_id}` has an invalid path. {validation_error}")
            if raw_test_id in generated_ids:
                raise ValueError(f"Generated duplicate test id `{raw_test_id}`.")
            generated_ids.add(raw_test_id)
            stored_item = {
                **test,
                "test_id": raw_test_id,
                "req_id": node_id,
                "type": test_type,
                "file_path": file_path,
                "interface_ids": normalize_string_list(test.get("interface_ids")),
                "first_line": str(test.get("first_line", "")).strip(),
            }
            stored.append(stored_item)
        return stored

    def _store_prepared_tests(self, tests: list[dict[str, Any]]) -> None:
        for test in tests:
            self.traceability.upsert_test(
                test_id=str(test.get("test_id", "") or "").strip(),
                req_id=str(test.get("req_id", "") or "").strip(),
                interface_ids=normalize_string_list(test.get("interface_ids")),
                type=str(test.get("type", "") or "").strip(),
                file_path=str(test.get("file_path", "") or "").strip() or None,
                first_line=str(test.get("first_line", "") or "").strip() or None,
                passed=None,
            )

    def _register_interface_edges(self, node_id: str, interface_id: str, interface: dict[str, Any]) -> None:
        for caller_id in normalize_string_list(interface.get("callers")):
            caller = self.traceability.get_interface(caller_id)
            if not caller:
                continue
            for source_req_id in caller.get("req_ids", []):
                if source_req_id and source_req_id != node_id:
                    self.traceability.insert_call_edge(
                        source_req_id=source_req_id,
                        target_req_id=node_id,
                        from_interface_id=caller_id,
                        to_interface_id=interface_id,
                        edge_type="cross_req",
                    )
        for callee_id in normalize_string_list(interface.get("callees")):
            callee = self.traceability.get_interface(callee_id)
            if not callee:
                continue
            for target_req_id in callee.get("req_ids", []):
                if target_req_id and target_req_id != node_id:
                    self.traceability.insert_call_edge(
                        source_req_id=node_id,
                        target_req_id=target_req_id,
                        from_interface_id=interface_id,
                        to_interface_id=callee_id,
                        edge_type="cross_req",
                    )

    def _mark_interfaces_implemented(self, interfaces: list[dict[str, Any]]) -> None:
        for interface in interfaces:
            interface_id = str(interface.get("interface_id", "") or "").strip()
            if interface_id:
                self.traceability.set_interface_implemented(interface_id, True)

    def _update_node_session(self, node_id: str, patch: dict[str, Any]) -> None:
        sessions.merge_node_session(node_id, patch)
        context_pipeline.cache.invalidate_db_layers(node_id)

    def _record_consecutive_failure(
        self,
        test_type: str,
        output: str,
        fingerprints: dict[str, list[str]],
        stop_set: set[str],
    ) -> None:
        """Track consecutive identical failures per layer for early stop."""
        if test_type in stop_set:
            return
        fingerprint = _failure_fingerprint(output)
        history = fingerprints[test_type]
        if history and history[-1] == fingerprint:
            history.append(fingerprint)
        else:
            history[:] = [fingerprint]
        if len(history) >= TDD_CONSECUTIVE_FAIL_STOP:
            stop_set.add(test_type)

    def _should_escalate(self, latest_output: str) -> bool:
        """Return True when a layer is "close to passing" and worth escalating.

        Escalation is only worthwhile when the failure count is small (<=
        TDD_FALLBACK_MAX_FAILED_TESTS) and a fallback model is configured.
        """
        if not TDD_FALLBACK_MODEL:
            return False
        main_model = getattr(self.test_driven_developer, "model", None)
        if isinstance(main_model, str) and main_model.strip() == TDD_FALLBACK_MODEL.strip():
            # 主模型与 fallback 相同 → "升级"只是同模型重跑，纯浪费预算，直接跳过
            return False
        failed_count = _count_failed_tests(latest_output)
        if failed_count is None:
            # 无法识别失败数（如 Playwright E2E）→ 不升级，避免烧钱
            return False
        return failed_count <= TDD_FALLBACK_MAX_FAILED_TESTS

    async def _log(
        self,
        agent_name: str,
        message: str,
        status: str | None = None,
        node_id: str | None = None,
    ) -> None:
        if self.log_cb is None:
            return
        result = self.log_cb(agent_name, message, status, node_id)
        if hasattr(result, "__await__"):
            await result


def collect_test_files(tests: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    for test in tests:
        file_path = str(test.get("file_path", "")).strip()
        if file_path and file_path not in seen:
            seen.append(file_path)
    return seen


def canonical_test_type(value: str) -> str | None:
    normalized = str(value or "").strip().lower()
    for test_type in TDD_BATCH_ORDER:
        if normalized == test_type.lower():
            return test_type
    return None


def summarize_interface_artifacts(interfaces: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(interfaces),
        "items": [
            {
                "id": str(item.get("interface_id", "") or "").strip(),
                "type": str(item.get("type", "") or "").strip(),
                "path": str(item.get("file_path", "") or "").strip(),
                "responsibility": str(item.get("responsibility", "") or item.get("name", "") or "").strip(),
            }
            for item in interfaces
            if isinstance(item, dict)
        ],
    }


def summarize_test_artifacts(tests: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(tests),
        "items": [
            {
                "id": str(item.get("test_id", "") or "").strip(),
                "type": str(item.get("type", "") or "").strip(),
                "path": str(item.get("file_path", "") or "").strip(),
                "interfaces": normalize_string_list(item.get("interface_ids")),
            }
            for item in tests
            if isinstance(item, dict)
        ],
    }


def normalize_workspace_relative_path(value: Any, workspace_path: str) -> str:
    path = normalize_windows_extended_prefix_text(value)
    if not path:
        return ""
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if path == "/workspace":
        return ""
    if path.startswith("/workspace/"):
        return path[len("/workspace/") :].lstrip("/")

    workspace = normalize_windows_extended_prefix_text(Path(workspace_path).expanduser().resolve()).rstrip("/")
    if path == workspace:
        return ""
    if path.startswith(workspace + "/"):
        return path[len(workspace) + 1 :].lstrip("/")
    return path.lstrip("/")


def summarize_batch_output(batch_output: str, max_lines: int = 30) -> str:
    lines = [line for line in (batch_output or "").splitlines() if line.strip()]
    if len(lines) > max_lines:
        lines = ["...[truncated]", *lines[-max_lines:]]
    return "\n".join(lines)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text or "")


def _count_failed_tests(output: str) -> int | None:
    """Extract the number of failed test assertions from Vitest-style output.

    Matches summary lines like `Tests  10 failed | 8 passed (18)`. Returns
    None when the output format is not recognized (e.g. Playwright E2E), so
    callers can fall back to a conservative policy.
    """
    plain = _strip_ansi(output)
    counts = [int(m) for m in re.findall(r"Tests\s+(\d+)\s+failed", plain)]
    if not counts:
        return None
    return sum(counts)


def _failure_fingerprint(output: str) -> str:
    """Build a stable failure fingerprint for consecutive-same-error detection."""
    plain = _strip_ansi(output)
    exit_code = ""
    key_lines: list[str] = []
    for line in plain.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Exit Code:") and not exit_code:
            exit_code = stripped
            continue
        lowered = stripped.lower()
        if "error" in lowered or "failed" in lowered or "expect" in lowered:
            key_lines.append(stripped[:240])
            if len(key_lines) >= 3:
                break
    return "|".join([exit_code, *key_lines])


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _strip_internal_fields(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if not str(key).startswith("_")}
