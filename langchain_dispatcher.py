from __future__ import annotations

import logging

from langchain.agents import create_agent
from langchain.tools import tool

from review_lib.env import hf_model, hf_provider, load_env
from review_lib.langchain_model import build_chat_model
from review_lib.langchain_tools import build_review_tools
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
from review_lib.report import extract_langchain_report, print_report

logger = logging.getLogger("langchain_dispatcher")


def _build_specialist_agent(aspect_key: str):
    return create_agent(
        model=build_chat_model(),
        tools=build_review_tools(),
        system_prompt=specialist_system(aspect_key),
    )


def _wrap_specialist(aspect_key: str):
    specialist = _build_specialist_agent(aspect_key)
    name = specialist_tool_name(aspect_key)
    description = specialist_tool_description(aspect_key)

    @tool(name, description=description)
    def call_specialist(brief: str) -> str:
        """Короткий plain-text бриф (одна строка, без JSON/messages)."""
        user_text = SPECIALIST_USER_TEMPLATE.format(
            aspect_key=aspect_key,
            brief=(brief or "").strip() or "review current diff",
        )
        logger.info("specialist_invoke aspect=%s brief=%s", aspect_key, brief[:300])
        result = specialist.invoke(
            {"messages": [{"role": "user", "content": user_text}]}
        )
        text = extract_langchain_report(result) or "Замечаний нет (пустой ответ специалиста)."
        logger.info(
            "specialist_done aspect=%s reply_len=%s preview=%s",
            aspect_key,
            len(text),
            text[:400],
        )
        return text

    return call_specialist


def build_dispatcher():
    load_env()
    specialist_tools = [_wrap_specialist(key) for key in ASPECT_KEYS]
    logger.info(
        "dispatcher specialists=%s",
        [specialist_tool_name(k) for k in ASPECT_KEYS],
    )
    return create_agent(
        model=build_chat_model(),
        tools=specialist_tools,
        system_prompt=DISPATCHER_SYSTEM,
    )


def main() -> None:
    configure_logging()
    logger.info(
        "starting LangChain dispatcher review model=%s provider=%s",
        hf_model(),
        hf_provider(),
    )
    dispatcher = build_dispatcher()
    result = dispatcher.invoke(
        {"messages": [{"role": "user", "content": USER_MESSAGE}]}
    )
    messages = result.get("messages") or []
    for msg in messages:
        msg_type = type(msg).__name__
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            logger.info("dispatcher_message type=%s tool_calls=%s", msg_type, tool_calls)
        name = getattr(msg, "name", None)
        if name or msg_type in {"ToolMessage", "FunctionMessage"}:
            content = getattr(msg, "content", "")
            logger.info(
                "dispatcher_message type=%s name=%s content=%s",
                msg_type,
                name,
                str(content)[:800],
            )
    report = extract_langchain_report(result)
    print_report(report, title="LangChain · dispatcher")


if __name__ == "__main__":
    main()
