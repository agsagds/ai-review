from __future__ import annotations

from haystack.tools import create_tool_from_function

from review_lib.tools_core import CORE_TOOL_FUNCS


def build_review_tools():
    return [create_tool_from_function(fn) for fn in CORE_TOOL_FUNCS]
