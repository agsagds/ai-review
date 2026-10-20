from __future__ import annotations

import logging

from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage

from review_lib.env import hf_model, hf_provider, load_env
from review_lib.haystack_model import build_chat_generator
from review_lib.haystack_tools import build_review_tools
from review_lib.logging_setup import configure_logging
from review_lib.prompts import SINGLE_SYSTEM, USER_MESSAGE
from review_lib.report import extract_haystack_report, message_text, print_report

logger = logging.getLogger("haystack_single")


def build_agent() -> Agent:
    load_env()
    return Agent(
        chat_generator=build_chat_generator(),
        tools=build_review_tools(),
        system_prompt=SINGLE_SYSTEM,
        max_agent_steps=24,
    )


def main() -> None:
    configure_logging()
    logger.info(
        "starting Haystack single-agent review model=%s provider=%s",
        hf_model(),
        hf_provider(),
    )
    agent = build_agent()
    result = agent.run(messages=[ChatMessage.from_user(USER_MESSAGE)])
    messages = result.get("messages") or []
    for msg in messages:
        role = getattr(msg, "role", None)
        text = message_text(msg)
        if role and str(role).lower() in {"tool", "function"}:
            logger.info("agent_message role=%s text=%s", role, text[:500])
        elif getattr(msg, "tool_calls", None):
            logger.info("agent_message role=%s tool_calls=%s", role, msg.tool_calls)
        elif text:
            logger.info("agent_message role=%s text=%s", role, text[:500])
    report = extract_haystack_report(result)
    print_report(report, title="Haystack · single agent")


if __name__ == "__main__":
    main()
