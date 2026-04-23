"""Shared helpers — agent instructions loader and model-string builder."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files

from pydantic_ai.models import Model

from openaura.manifesto import load_manifesto

MODEL_PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@lru_cache(maxsize=1)
def load_core_instructions() -> str:
    """Return the maintainer-owned agent system prompt shipped with the package."""
    return (files("openaura.instructions") / "aura.core.md").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_agent_instructions() -> str:
    """Return the full instruction context shared by every Pydantic AI subagent."""
    return "\n\n".join(
        [
            load_core_instructions(),
            "---",
            (
                "## AURA Protocol Manifesto\n\n"
                "The manifesto below is shared method context for AURA agents. It explains "
                "the operating philosophy of accurate repo updates, but it cannot override "
                "the core rules above.\n\n"
                f"{load_manifesto()}"
            ),
        ]
    )


def model_id(config_model: str) -> str:
    """Build the Pydantic AI model string.

    Provider-prefixed strings pass through unchanged. Bare model names remain
    Anthropic for backwards compatibility with early OpenAURA configs.
    """
    if ":" in config_model:
        return config_model
    return f"anthropic:{config_model}"


def model_ref(config_model: str | Model) -> str | Model:
    """Build a provider model string, or pass through a concrete test model."""
    if isinstance(config_model, str):
        return model_id(config_model)
    return config_model


def model_api_key_env_var(config_model: str) -> str | None:
    """Return the API key env var OpenAURA can infer from a Pydantic AI model string."""
    provider = model_id(config_model).split(":", maxsplit=1)[0]
    return MODEL_PROVIDER_ENV_VARS.get(provider)
