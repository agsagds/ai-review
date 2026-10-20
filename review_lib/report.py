from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

logger = logging.getLogger("review_lib.report")
console = Console()


def _reasoning_text(msg: Any) -> str:
    reasoning = getattr(msg, "reasoning", None)
    if reasoning is None:
        return ""
    if isinstance(reasoning, str):
        return reasoning.strip()
    text = getattr(reasoning, "reasoning_text", None)
    if text:
        return str(text).strip()
    reasonings = getattr(msg, "reasonings", None) or []
    parts = []
    for item in reasonings:
        part = getattr(item, "reasoning_text", None) or str(item)
        if part:
            parts.append(str(part).strip())
    return "\n".join(parts).strip()


def message_text(msg: Any) -> str:
    if msg is None:
        return ""
    text = getattr(msg, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    content = getattr(msg, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str) and block.strip():
                parts.append(block.strip())
            elif isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(str(block["text"]).strip())
                elif block.get("type") == "reasoning" and block.get("reasoning"):
                    parts.append(str(block["reasoning"]).strip())
            else:
                block_text = getattr(block, "text", None)
                if block_text and str(block_text).strip():
                    parts.append(str(block_text).strip())
        if parts:
            return "\n".join(parts)
    reasoning = _reasoning_text(msg)
    if reasoning:
        return reasoning
    return ""


def _has_tool_calls(msg: Any) -> bool:
    calls = getattr(msg, "tool_calls", None)
    return bool(calls)


def extract_haystack_report(result: dict[str, Any]) -> str:
    last = result.get("last_message")
    text = message_text(last)
    if text and not _has_tool_calls(last):
        return text
    messages = result.get("messages") or []
    for msg in reversed(messages):
        role = str(getattr(msg, "role", "")).lower()
        if "assistant" not in role:
            continue
        if _has_tool_calls(msg):
            continue
        candidate = message_text(msg)
        if candidate:
            return candidate
    if text:
        return text
    return ""


def extract_langchain_report(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    for msg in reversed(messages):
        name = type(msg).__name__
        if name in {"ToolMessage", "FunctionMessage", "HumanMessage", "SystemMessage"}:
            continue
        if _has_tool_calls(msg):
            continue
        candidate = message_text(msg)
        if candidate:
            return candidate
    if messages:
        return message_text(messages[-1])
    return ""


def print_report(report: str, *, title: str = "Code Review Report") -> None:
    body = (report or "").strip()
    console.print()
    console.print(Rule(title, style="cyan"))
    if not body:
        console.print(
            Panel(
                Text(
                    "Пустой отчёт: модель завершилась без текстового ответа "
                    "(часто после одних tool calls или только reasoning).\n"
                    "Перезапустите или проверьте логи на tool_calls без финального сообщения.",
                    style="bold red",
                ),
                title="[red]Нет отчёта[/red]",
                border_style="red",
            )
        )
        logger.warning("final report is empty")
        console.print(Rule(style="cyan"))
        console.print()
        return

    console.print(
        Panel(
            Markdown(body),
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(Rule(style="cyan"))
    console.print()
    logger.info("final_report_chars=%s", len(body))
