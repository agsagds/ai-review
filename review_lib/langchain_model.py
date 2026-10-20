from __future__ import annotations

import logging

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from review_lib.env import hf_model, hf_provider

logger = logging.getLogger("review_lib.langchain_model")


def build_chat_model() -> ChatHuggingFace:
    model = hf_model()
    provider = hf_provider()
    logger.info("langchain HF endpoint model=%s provider=%s", model, provider)
    kwargs: dict = {
        "repo_id": model,
        "temperature": 0.1,
        "max_new_tokens": 4096,
        # Qwen3.8 on Cerebras otherwise burns the token budget on hidden reasoning
        # and returns empty assistant content (finish_reason=length).
        "model_kwargs": {"extra_body": {"reasoning_effort": "none"}},
    }
    if provider and provider != "auto":
        kwargs["provider"] = provider
    llm = HuggingFaceEndpoint(**kwargs)
    return ChatHuggingFace(llm=llm)
