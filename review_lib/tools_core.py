from __future__ import annotations

import logging
from typing import Annotated

from review_lib.fixtures import (
    ASPECT_CHECKLISTS,
    FLOOR_TESTS_EXISTING,
    GIT_DIFF,
    LSP_INDEX,
    PROJECT_TREE,
    TASK_DESCRIPTION,
)
from review_lib.prompts import ASPECT_KEYS

logger = logging.getLogger("review_lib.tools")


def _log_call(name: str, **kwargs: object) -> None:
    logger.info("tool_call name=%s args=%s", name, kwargs)


def _log_result(name: str, result: str) -> str:
    preview = result if len(result) <= 800 else result[:800] + f"... <truncated {len(result)} chars>"
    logger.info("tool_result name=%s\n%s", name, preview)
    return result


def git_diff_tool() -> str:
    """Return the unified git diff for the open AdCP change (3 files)."""
    _log_call("git_diff_tool")
    return _log_result("git_diff_tool", GIT_DIFF)


def project_tree_map_tool() -> str:
    """Return a static file tree map of the AdCP Rust workspace."""
    _log_call("project_tree_map_tool")
    return _log_result("project_tree_map_tool", PROJECT_TREE)


def task_description_tool() -> str:
    """Return the task / acceptance description for the open change."""
    _log_call("task_description_tool")
    return _log_result("task_description_tool", TASK_DESCRIPTION)


def review_aspect_tool(
    aspect: Annotated[
        str,
        "One of: logic_defects, input_validation, interfaces_compatibility, "
        "resources_error_handling, concurrency_sync, tests",
    ],
) -> str:
    """Return the review checklist for a single aspect key."""
    _log_call("review_aspect_tool", aspect=aspect)
    key = aspect.strip()
    if key not in ASPECT_CHECKLISTS:
        known = ", ".join(ASPECT_KEYS)
        result = f"Unknown aspect `{key}`. Known keys: {known}."
        return _log_result("review_aspect_tool", result)
    result = f"aspect: {key}\nchecklist:\n{ASPECT_CHECKLISTS[key]}"
    return _log_result("review_aspect_tool", result)


def lsp_related_code_tool(
    symbol: Annotated[
        str,
        "Symbol name to resolve (e.g. enforce_floor, run_auction, AuctionState, "
        "AuctionError, FloorError, redact_publisher_token, persist_bid_stub)",
    ],
) -> str:
    """Return mocked LSP definition and usages for a symbol related to the diff."""
    _log_call("lsp_related_code_tool", symbol=symbol)
    key = symbol.strip()
    if key in LSP_INDEX:
        body = LSP_INDEX[key]
        if key in {"enforce_floor", "run_auction"}:
            body = body + "\n\nrelated_test_file:\n" + FLOOR_TESTS_EXISTING
        return _log_result("lsp_related_code_tool", body)
    known = ", ".join(sorted(LSP_INDEX))
    result = f"No LSP data for `{key}`. Known symbols: {known}."
    return _log_result("lsp_related_code_tool", result)


CORE_TOOL_FUNCS = (
    git_diff_tool,
    project_tree_map_tool,
    task_description_tool,
    review_aspect_tool,
    lsp_related_code_tool,
)
