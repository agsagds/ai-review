from __future__ import annotations

import json
import logging

logger = logging.getLogger("review_lib.haystack_hf_patch")
_applied = False


def apply_empty_tool_args_patch() -> None:
    """Haystack HF integration skips tool calls when arguments == {}.

    ``if arguments:`` treats an empty dict as false, so parameter-less tools
    (git_diff_tool, task_description_tool, ...) never execute and the agent loops.
    """
    global _applied
    if _applied:
        return

    from haystack.dataclasses import ToolCall
    import haystack_integrations.components.generators.huggingface_api.chat.chat_generator as mod

    def _convert_hfapi_tool_calls(hfapi_tool_calls):
        if not hfapi_tool_calls:
            return []
        tool_calls = []
        for hfapi_tc in hfapi_tool_calls:
            hf_arguments = hfapi_tc.function.arguments
            arguments = None
            if isinstance(hf_arguments, dict):
                arguments = hf_arguments
            elif isinstance(hf_arguments, str):
                try:
                    arguments = json.loads(hf_arguments)
                except json.JSONDecodeError:
                    logger.warning(
                        "malformed tool args id=%s name=%s args=%s",
                        hfapi_tc.id,
                        hfapi_tc.function.name,
                        hf_arguments,
                    )
                    continue
            else:
                logger.warning(
                    "unexpected tool args type=%s id=%s name=%s",
                    type(hf_arguments),
                    hfapi_tc.id,
                    hfapi_tc.function.name,
                )
                continue
            if arguments is None:
                continue
            tool_calls.append(
                ToolCall(
                    tool_name=hfapi_tc.function.name,
                    arguments=arguments,
                    id=hfapi_tc.id,
                )
            )
        return tool_calls

    mod._convert_hfapi_tool_calls = _convert_hfapi_tool_calls
    _applied = True
    logger.info("applied Haystack HF empty-tool-args patch")
