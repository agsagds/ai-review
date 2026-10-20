from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_HF_MODEL = "Qwen/Qwen3.8-27B"
DEFAULT_HF_PROVIDER = "cerebras"


def load_env() -> str:
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN is missing. Set it in .env (see .env.example).")
    os.environ.setdefault("HF_API_TOKEN", token)
    os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", token)
    os.environ.setdefault("HF_TOKEN", token)
    return token


def hf_model() -> str:
    return os.environ.get("HF_MODEL", DEFAULT_HF_MODEL).strip() or DEFAULT_HF_MODEL


def hf_provider() -> str:
    """Inference Providers routing: specific name, or policy auto/cheapest/fastest/preferred."""
    return (
        os.environ.get("HF_PROVIDER", DEFAULT_HF_PROVIDER).strip()
        or DEFAULT_HF_PROVIDER
    )


def hf_router_model_id() -> str:
    """OpenAI-compatible router form: model[:provider_or_policy]."""
    model = hf_model()
    provider = hf_provider()
    if ":" in model:
        return model
    return f"{model}:{provider}"


HF_MODEL = DEFAULT_HF_MODEL
