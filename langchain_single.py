from __future__ import annotations

import logging

from langchain.agents import create_agent

from review_lib.env import hf_model, hf_provider, load_env
from review_lib.langchain_model import build_chat_model
from review_lib.langchain_tools import build_review_tools
from review_lib.logging_setup import configure_logging
from review_lib.prompts import SINGLE_SYSTEM, USER_MESSAGE
from review_lib.report import extract_langchain_report, message_text, print_report

logger = logging.getLogger("langchain_single")


def build_agent():
    load_env()
    return create_agent(
        model=build_chat_model(),
        tools=build_review_tools(),
        system_prompt=SINGLE_SYSTEM,
    )


def _log_messages(messages: list) -> None:
    for msg in messages:
        msg_type = type(msg).__name__
        content = message_text(msg)
        tool_calls = getattr(msg, "tool_calls", None)
        name = getattr(msg, "name", None)
        if tool_calls:
            logger.info("agent_message type=%s tool_calls=%s", msg_type, tool_calls)
        if name or msg_type in {"ToolMessage", "FunctionMessage"}:
            logger.info(
                "agent_message type=%s name=%s content=%s",
                msg_type,
                name,
                content[:500],
            )
        elif content and msg_type not in {"HumanMessage", "SystemMessage"}:
            logger.info("agent_message type=%s content=%s", msg_type, content[:500])


def main() -> None:
    configure_logging()
    logger.info(
        "starting LangChain single-agent review model=%s provider=%s",
        hf_model(),
        hf_provider(),
    )
    agent = build_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": USER_MESSAGE}]})
    _log_messages(result.get("messages") or [])
    report = extract_langchain_report(result)
    print_report(report, title="LangChain · single agent")


if __name__ == "__main__":
    main()
