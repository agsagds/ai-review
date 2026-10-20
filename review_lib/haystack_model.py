from __future__ import annotations

import logging

from haystack_integrations.components.generators.huggingface_api import (
    HuggingFaceAPIChatGenerator,
)
from haystack.utils import Secret

from review_lib.env import hf_model, hf_provider
from review_lib.haystack_hf_patch import apply_empty_tool_args_patch

logger = logging.getLogger("review_lib.haystack_model")

apply_empty_tool_args_patch()

GENERATION_KWARGS = {
    "max_tokens": 4096,
    "temperature": 0.1,
    # Qwen3.8 on Cerebras otherwise burns the token budget on hidden reasoning
    # and returns empty assistant content (finish_reason=length).
    "extra_body": {"reasoning_effort": "none"},
}


def build_chat_generator() -> HuggingFaceAPIChatGenerator:
    model = hf_model()
    provider = hf_provider()
    logger.info("haystack HF generator model=%s provider=%s", model, provider)
    api_params: dict = {"model": model}
    if provider and provider != "auto":
        api_params["provider"] = provider
    return HuggingFaceAPIChatGenerator(
        api_type="serverless_inference_api",
        api_params=api_params,
        token=Secret.from_env_var("HF_TOKEN"),
        generation_kwargs=dict(GENERATION_KWARGS),
    )
