"""Pydantic request/response models for the ARC Studio REST API."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Stage(str, Enum):
    DESIGN = "DESIGN"
    IMPLEMENT = "IMPLEMENT"
    TEST = "TEST"


# ---------------------------------------------------------------------------
# /api/generate-tree
# ---------------------------------------------------------------------------
class GenerateTreeRequest(BaseModel):
    requirement: str = Field(..., description="自然语言需求描述")
    app_type: str = Field(default="web", description="应用类型，默认 web")
    # Optional LLM credentials; when omitted the backend falls back to its
    # configured defaults and finally to a built-in mock template.
    api_key: Optional[str] = Field(default=None, description="OpenAI 兼容 API Key")
    base_url: Optional[str] = Field(default=None, description="OpenAI 兼容 Base URL")
    model: Optional[str] = Field(default=None, description="模型名称")


class TreeNodeResponse(BaseModel):
    id: str
    parent: Optional[str] = None
    name: str
    desc: str = ""
    status: str = "PENDING"
    stage: str = "DESIGN"


class GenerateTreeResponse(BaseModel):
    title: str
    nodes: list[TreeNodeResponse]
    source: str = Field(
        default="mock",
        description="需求树来源：llm 表示来自大模型，mock 表示来自内置模板",
    )
    requirement_yaml: str = Field(
        default="",
        description="转换后的编译器可接受 YAML 文本",
    )


# ---------------------------------------------------------------------------
# /api/compile
# ---------------------------------------------------------------------------
class ModelSelection(BaseModel):
    design: Optional[str] = None
    test: Optional[str] = None
    development: Optional[str] = None


class CompileRequest(BaseModel):
    requirement_text: str = Field(..., description="用户的自然语言需求")
    requirement_yaml: Optional[str] = Field(
        default=None,
        description="可选：直接传入 YAML 格式需求文档；不传则后端自动生成",
    )
    app_type: str = Field(default="web")
    models: Optional[ModelSelection] = None
    api_key: str = Field(..., description="编译器使用的 OpenAI 兼容 API Key")
    base_url: str = Field(..., description="编译器使用的 OpenAI 兼容 Base URL")
    model: Optional[str] = Field(default=None, description="默认模型名")


class CompileResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


# ---------------------------------------------------------------------------
# /api/status/{task_id}
# ---------------------------------------------------------------------------
class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str


class NodeStatusItem(BaseModel):
    id: str
    status: NodeStatus = NodeStatus.PENDING
    stage: Stage = Stage.DESIGN


class TaskStats(BaseModel):
    completed_nodes: int = 0
    total_nodes: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost: float = 0.0


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = 0
    current_stage: str = ""
    current_node: str = Field(default="", description="当前正在处理的节点 ID，如 REQ-1-2；没有则空字符串")
    nodes: list[NodeStatusItem] = []
    logs: list[LogEntry] = []
    stats: TaskStats = TaskStats()


# ---------------------------------------------------------------------------
# /api/result/{task_id}
# ---------------------------------------------------------------------------
class TestResultItem(BaseModel):
    name: str
    status: str  # PASSED / FAILED
    error: Optional[str] = None


class ResultSummary(BaseModel):
    total_nodes: int = 0
    passed_nodes: int = 0
    failed_nodes: int = 0
    total_time_seconds: float = 0.0
    total_cost: float = 0.0


class TaskResultResponse(BaseModel):
    task_id: str
    status: TaskStatus
    preview_url: str = ""
    download_url: str = ""
    test_results: list[TestResultItem] = []
    output_dir: str = ""
    summary: ResultSummary = ResultSummary()


class CancelResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
