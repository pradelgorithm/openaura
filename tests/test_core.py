from __future__ import annotations

from openaura.agents._core import model_api_key_env_var, model_id


def test_model_id_defaults_bare_names_to_anthropic():
    assert model_id("claude-sonnet-4-6") == "anthropic:claude-sonnet-4-6"
    assert model_id("openai:gpt-5.2") == "openai:gpt-5.2"


def test_model_api_key_env_var_for_supported_providers():
    assert model_api_key_env_var("claude-sonnet-4-6") == "ANTHROPIC_API_KEY"
    assert model_api_key_env_var("anthropic:claude-sonnet-4-6") == "ANTHROPIC_API_KEY"
    assert model_api_key_env_var("openai:gpt-5.2") == "OPENAI_API_KEY"
    assert model_api_key_env_var("ollama:llama3.2") is None
