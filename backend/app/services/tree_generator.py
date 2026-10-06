"""Natural-language requirement -> structured requirement tree.

Primary path (方案A): call an OpenAI-compatible chat/completions endpoint and
ask for a strict JSON requirement tree. Fallback (方案B): a built-in template
chosen by app type / keywords, so the API is always usable even without a key.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import httpx

from app import config
from app.models import GenerateTreeResponse, TreeNodeResponse
from app.utils.yaml_helper import tree_to_compiler_yaml


_SYSTEM_PROMPT = (
    "你是一名资深产品需求分析师。用户会用自然语言描述一个想做的应用，"
    "你需要把它拆解为一棵层级化的需求树。"
    "严格只输出 JSON，不要输出任何解释或 markdown 代码块标记。"
    "JSON 结构必须为："
    '{"title": "应用标题", "nodes": ['
    '{"id":"REQ-1","parent":null,"name":"应用总览","desc":"...","stage":"DESIGN"},'
    '{"id":"REQ-1-1","parent":"REQ-1","name":"功能模块A","desc":"...","stage":"IMPLEMENT"}'
    ']}。'
    "规则：根节点 parent 为 null、id 为 REQ-1；子节点 id 形如 REQ-1-1；"
    "stage 只能是 DESIGN / IMPLEMENT / TEST；"
    "拆解出 3-6 个原子功能模块，desc 用一句话描述该模块要做什么。"
)


def _build_user_prompt(requirement: str, app_type: str) -> str:
    return f"应用类型：{app_type}\n用户需求：{requirement}\n请输出需求树 JSON。"


def _try_llm(
    requirement: str,
    app_type: str,
    api_key: str,
    base_url: str,
    model: str,
) -> Optional[GenerateTreeResponse]:
    """Call the LLM and return a parsed tree, or None on any failure."""
    if not api_key or not base_url:
        return None

    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(requirement, app_type)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except Exception:
        return None

    tree = _parse_tree_content(content)
    if tree is None:
        return None
    title, nodes = tree
    return _build_response(title, nodes, source="llm")


def _parse_tree_content(content: str) -> Optional[tuple[str, list[TreeNodeResponse]]]:
    """Extract JSON from an LLM response, tolerating code fences."""
    text = content.strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
    except Exception:
        # Try to grab the outermost {...}
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            obj = json.loads(match.group(0))
        except Exception:
            return None

    title = obj.get("title") or obj.get("name") or "未命名应用"
    raw_nodes = obj.get("nodes") or []
    nodes: list[TreeNodeResponse] = []
    for n in raw_nodes:
        try:
            nodes.append(
                TreeNodeResponse(
                    id=str(n["id"]),
                    parent=n.get("parent"),
                    name=str(n.get("name", n["id"])),
                    desc=str(n.get("desc", n.get("description", ""))),
                    status="PENDING",
                    stage=str(n.get("stage", "DESIGN")),
                )
            )
        except Exception:
            continue
    if not nodes:
        return None
    return title, nodes


# ---------------------------------------------------------------------------
# Mock templates (方案B)
# ---------------------------------------------------------------------------
def _mock_tree(requirement: str, app_type: str) -> tuple[str, list[TreeNodeResponse]]:
    text = requirement.lower()

    # Pick a theme by keyword.
    if any(k in text for k in ("待办", "todo", "任务清单", "checklist")):
        title = "待办清单应用"
        modules = [
            ("添加任务", "用户可以输入任务标题并添加到清单。"),
            ("完成任务", "用户可以勾选复选框将任务标记为已完成。"),
            ("删除任务", "用户可以删除不再需要的任务。"),
            ("任务列表", "按时间顺序展示所有任务及完成状态。"),
        ]
    elif any(k in text for k in ("票", "ticket", "预订", "booking", "火车", "电影")):
        title = "在线预订系统"
        modules = [
            ("账号注册登录", "访客注册账号并登录系统。"),
            ("资源搜索", "按条件搜索可预订的车次/场次。"),
            ("提交订单", "登录后填写乘客/联系信息并提交预订。"),
            ("订单持久化", "账号、会话与已确认订单在刷新后仍可恢复。"),
        ]
    elif any(k in text for k in ("博客", "blog", "文章", "笔记", "note")):
        title = "内容笔记应用"
        modules = [
            ("编辑内容", "用户可以创建和编辑富文本内容。"),
            ("内容列表", "按时间展示已保存的内容条目。"),
            ("查看详情", "点击条目查看完整内容。"),
            ("删除内容", "用户可以删除不需要的内容。"),
        ]
    else:
        title = requirement.strip().splitlines()[0][:20] if requirement.strip() else "通用业务应用"
        modules = [
            ("数据录入", "用户可以录入核心业务数据。"),
            ("数据列表", "展示已录入的数据条目。"),
            ("查看详情", "查看单条数据的完整信息。"),
            ("删除数据", "用户可以删除不需要的数据条目。"),
        ]

    nodes: list[TreeNodeResponse] = [
        TreeNodeResponse(id="REQ-1", parent=None, name=title, desc=requirement[:120], status="PENDING", stage="DESIGN"),
    ]
    for idx, (name, desc) in enumerate(modules, start=1):
        nodes.append(
            TreeNodeResponse(
                id=f"REQ-1-{idx}",
                parent="REQ-1",
                name=name,
                desc=desc,
                status="PENDING",
                stage="IMPLEMENT",
            )
        )
    return title, nodes


def _build_response(title: str, nodes: list[TreeNodeResponse], source: str) -> GenerateTreeResponse:
    yaml_text = tree_to_compiler_yaml(title, nodes)
    return GenerateTreeResponse(
        title=title,
        nodes=nodes,
        source=source,
        requirement_yaml=yaml_text,
    )


class TreeGeneratorService:
    def generate(
        self,
        requirement: str,
        app_type: str = "web",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> GenerateTreeResponse:
        key = (api_key or config.DEFAULT_OPENAI_API_KEY).strip()
        url = (base_url or config.DEFAULT_OPENAI_BASE_URL).strip()
        mdl = (model or config.DEFAULT_DESIGNER_MODEL).strip()

        result = _try_llm(requirement, app_type, key, url, mdl)
        if result is not None:
            return result

        title, nodes = _mock_tree(requirement, app_type)
        return _build_response(title, nodes, source="mock")
