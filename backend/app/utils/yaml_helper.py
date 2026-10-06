"""YAML reading/writing and requirement-tree -> compiler-YAML conversion.

The ARC compiler expects a single root node with recursive ``children``. Node
types are ``FOLDER`` (internal) and ``ATOMIC`` (leaf requirement). See
``agentic-requirement-compiler/example/ticketbooking-quickstart/requirements.yaml``.
"""

from __future__ import annotations

from typing import Any

import yaml

from app.models import TreeNodeResponse


def dump_yaml(data: Any) -> str:
    """Serialize ``data`` to a YAML string (UTF-8, no extra line breaks noise)."""
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )


def write_yaml(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dump_yaml(data))


def load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _node_description(node: TreeNodeResponse) -> str:
    parts: list[str] = []
    if node.desc:
        parts.append(node.desc.strip())
    return "\n".join(parts) if parts else f"{node.name} 功能需求"


def tree_to_compiler_yaml(title: str, nodes: list[TreeNodeResponse]) -> str:
    """Convert the flat requirement tree returned by /api/generate-tree into the
    recursive YAML structure the compiler consumes.

    The root node (parent == None) becomes id ``ROOT`` / type FOLDER. Every other
    node becomes an ATOMIC child; children are grouped under their parent.
    """
    # Index nodes by id for parent lookup.
    by_id: dict[str, TreeNodeResponse] = {n.id: n for n in nodes}
    roots = [n for n in nodes if n.parent is None]
    root = roots[0] if roots else (nodes[0] if nodes else None)

    children_of: dict[str | None, list[TreeNodeResponse]] = {}
    for node in nodes:
        children_of.setdefault(node.parent, []).append(node)

    def build_node(node: TreeNodeResponse) -> dict[str, Any]:
        child_nodes = children_of.get(node.id, [])
        is_leaf = not child_nodes
        entry: dict[str, Any] = {
            "id": node.id,
            "name": node.name,
            "type": "ATOMIC" if is_leaf else "FOLDER",
            "description": _node_description(node),
            "dependencies": [],
        }
        if child_nodes:
            entry["children"] = [build_node(c) for c in child_nodes]
        if is_leaf:
            entry["scenarios"] = [
                {
                    "name": f"{node.name} 主流程",
                    "steps": [
                        {"keyword": "GIVEN", "content": f"用户准备使用 {node.name} 功能。"},
                        {"keyword": "WHEN", "content": f"用户触发 {node.name} 相关操作。"},
                        {"keyword": "THEN", "content": f"系统正确完成 {node.name} 并给出反馈。"},
                    ],
                }
            ]
        return entry

    if root is None:
        root_entry: dict[str, Any] = {
            "id": "ROOT",
            "name": title or "未命名应用",
            "type": "FOLDER",
            "description": title or "未命名应用",
            "dependencies": [],
            "children": [],
        }
    else:
        root_entry = build_node(root)
        root_entry["id"] = "ROOT"
        root_entry["name"] = title or root.name
        # Ensure direct children of ROOT are attached (flat tree handling).
        direct = children_of.get(root.id, [])
        if direct and "children" not in root_entry:
            root_entry["children"] = [build_node(c) for c in direct]

    return dump_yaml(root_entry)
