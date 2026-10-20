from __future__ import annotations

import logging
from typing import Annotated

from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage
from haystack.tools import create_tool_from_function

from review_lib.env import hf_model, hf_provider, load_env
from review_lib.haystack_model import build_chat_generator
from review_lib.haystack_tools import build_review_tools
from review_lib.logging_setup import configure_logging
from review_lib.prompts import (
    ASPECT_KEYS,
    DISPATCHER_SYSTEM,
    SPECIALIST_USER_TEMPLATE,
    USER_MESSAGE,
    specialist_system,
    specialist_tool_description,
    specialist_tool_name,
)
from review_lib.report import (
    extract_haystack_report,
    message_text,
    print_report,
)

logger = logging.getLogger("haystack_dispatcher")


def _run_specialist(aspect_key: str, brief: str) -> str:
    agent = Agent(
        chat_generator=build_chat_generator(),
        tools=build_review_tools(),
        system_prompt=specialist_system(aspect_key),
        max_agent_steps=16,
    )
    user_text = SPECIALIST_USER_TEMPLATE.format(
        aspect_key=aspect_key, brief=(brief or "").strip() or "review current diff"
    )
    logger.info("specialist_invoke aspect=%s brief=%s", aspect_key, brief[:300])
    result = agent.run(messages=[ChatMessage.from_user(user_text)])
    report = extract_haystack_report(result)
    if not report:
        last = result.get("last_message")
        report = message_text(last) or "Замечаний нет (пустой ответ специалиста)."
    logger.info(
        "specialist_done aspect=%s reply_len=%s preview=%s",
        aspect_key,
        len(report),
        report[:400],
    )
    return report


def build_specialist_tool(aspect_key: str):
    name = specialist_tool_name(aspect_key)
    description = specialist_tool_description(aspect_key)

    def invoke(
        brief: Annotated[
            str,
            "Короткий plain-text бриф для специалиста (одна строка, без JSON/messages).",
        ],
    ) -> str:
        return _run_specialist(aspect_key, brief)

    invoke.__name__ = name
    invoke.__doc__ = description
    return create_tool_from_function(invoke, name=name, description=description)


def build_dispatcher() -> Agent:
    load_env()
    specialists = [build_specialist_tool(key) for key in ASPECT_KEYS]
    logger.info(
        "dispatcher specialists=%s",
        [specialist_tool_name(k) for k in ASPECT_KEYS],
    )
    return Agent(
        chat_generator=build_chat_generator(),
        tools=specialists,
        system_prompt=DISPATCHER_SYSTEM,
        max_agent_steps=16,
        tool_concurrency_limit=2,
    )


def main() -> None:
    configure_logging()
    logger.info(
        "starting Haystack dispatcher review model=%s provider=%s",
        hf_model(),
        hf_provider(),
    )
    dispatcher = build_dispatcher()
    result = dispatcher.run(messages=[ChatMessage.from_user(USER_MESSAGE)])
    messages = result.get("messages") or []
    for msg in messages:
        role = getattr(msg, "role", None)
        text = message_text(msg)
        if role and str(role).lower() in {"tool", "function"}:
            logger.info("dispatcher_message role=%s text=%s", role, text[:800])
        elif getattr(msg, "tool_calls", None):
            logger.info(
                "dispatcher_message role=%s tool_calls=%s", role, msg.tool_calls
            )
        elif text:
            logger.info("dispatcher_message role=%s text=%s", role, text[:800])
    report = extract_haystack_report(result)
    print_report(report, title="Haystack · dispatcher")


if __name__ == "__main__":
    main()
