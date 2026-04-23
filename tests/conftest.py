"""Shared pytest fixtures."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from openaura.agents.deps import AuraDeps
from openaura.models.config import (
    AuraConfig,
    AzureDevOpsConfig,
    GitHubConfig,
    SignalsConfig,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(source: str, name: str) -> Any:
    return json.loads((FIXTURES / source / f"{name}.json").read_text())


@pytest.fixture
def sample_config() -> AuraConfig:
    return AuraConfig(
        project="test-project",
        trigger="weekly",
        model="anthropic:claude-sonnet-4-6",
        signals=SignalsConfig(
            github=GitHubConfig(repo="openaura/openaura"),
            azuredevops=AzureDevOpsConfig(repos=["backend"]),
        ),
    )


@pytest.fixture
def github_only_config() -> AuraConfig:
    return AuraConfig(
        project="test-project",
        signals=SignalsConfig(github=GitHubConfig(repo="openaura/openaura")),
    )


@pytest.fixture
def test_env() -> dict[str, str]:
    return {
        "ANTHROPIC_API_KEY": "sk-test",
        "OPENAI_API_KEY": "sk-test",
        "GITHUB_TOKEN": "ghp-test",
        "AZURE_DEVOPS_ORG": "acme",
        "AZURE_DEVOPS_PROJECT": "demo",
        "AZURE_DEVOPS_TOKEN": "ado-test",
    }


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(timeout=5) as client:
        yield client


@pytest.fixture
def deps_factory(test_env: dict[str, str]):
    async def _build(config: AuraConfig, client: httpx.AsyncClient) -> AuraDeps:
        now = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
        return AuraDeps(
            config=config,
            project_context="Sprint goal: ship the thing.",
            http=client,
            period_start=datetime(2026, 4, 16, 0, 0, 0, tzinfo=UTC),
            period_end=now,
            env=test_env,
        )

    return _build
