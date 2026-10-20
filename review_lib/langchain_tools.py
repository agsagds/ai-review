from __future__ import annotations

from langchain.tools import tool

from review_lib.tools_core import (
    git_diff_tool as _git_diff,
    lsp_related_code_tool as _lsp,
    project_tree_map_tool as _tree,
    review_aspect_tool as _aspect,
    task_description_tool as _task,
)


@tool
def git_diff_tool() -> str:
    """Return the unified git diff for the open AdCP change (3 files)."""
    return _git_diff()


@tool
def project_tree_map_tool() -> str:
    """Return a static file tree map of the AdCP Rust workspace."""
    return _tree()


@tool
def task_description_tool() -> str:
    """Return the task / acceptance description for the open change."""
    return _task()


@tool
def review_aspect_tool(aspect: str) -> str:
    """Return the review checklist for a single aspect key."""
    return _aspect(aspect)


@tool
def lsp_related_code_tool(symbol: str) -> str:
    """Return mocked LSP definition and usages for a symbol related to the diff."""
    return _lsp(symbol)


def build_review_tools():
    return [
        git_diff_tool,
        project_tree_map_tool,
        task_description_tool,
        review_aspect_tool,
        lsp_related_code_tool,
    ]
