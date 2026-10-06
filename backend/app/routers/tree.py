"""Endpoints for generating a structured requirement tree from natural language."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import GenerateTreeRequest, GenerateTreeResponse
from app.services.tree_generator import TreeGeneratorService

router = APIRouter(prefix="/api", tags=["requirement-tree"])
_tree_service = TreeGeneratorService()


@router.post("/generate-tree", response_model=GenerateTreeResponse)
def generate_tree(req: GenerateTreeRequest) -> GenerateTreeResponse:
    """Turn a natural-language requirement into a structured requirement tree.

    Tries an OpenAI-compatible LLM first; falls back to a built-in mock template
    when no credentials are available or the call fails. The response always
    includes a compiler-ready YAML representation.
    """
    return _tree_service.generate(
        requirement=req.requirement,
        app_type=req.app_type,
        api_key=req.api_key,
        base_url=req.base_url,
        model=req.model,
    )
