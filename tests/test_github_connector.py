"""GitHub connector tests — drive fixtures through respx."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from openaura.connectors.github import GitHubConnector
from openaura.models.config import GitHubConfig
from tests.conftest import load_fixture


@pytest.mark.asyncio
async def test_github_fetch_parses_all_signal_types():
    since = datetime(2026, 4, 16, 0, 0, 0, tzinfo=UTC)
    config = GitHubConfig(repo="openaura/openaura")

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get("https://api.github.com/repos/openaura/openaura/pulls").mock(
            return_value=httpx.Response(200, json=load_fixture("github", "pulls_closed"))
        )
        respx_mock.get(
            "https://api.github.com/repos/openaura/openaura/issues",
            params={"state": "closed"},
        ).mock(return_value=httpx.Response(200, json=load_fixture("github", "issues_closed")))
        respx_mock.get("https://api.github.com/repos/openaura/openaura/commits").mock(
            return_value=httpx.Response(200, json=load_fixture("github", "commits"))
        )
        respx_mock.get(
            "https://api.github.com/repos/openaura/openaura/issues",
            params={"state": "open", "labels": "blocker"},
        ).mock(return_value=httpx.Response(200, json=load_fixture("github", "issues_open_blocker")))
        respx_mock.get(
            "https://api.github.com/repos/openaura/openaura/issues",
            params={"state": "open", "labels": "bug"},
        ).mock(return_value=httpx.Response(200, json=load_fixture("github", "issues_open_bug")))
        respx_mock.get("https://api.github.com/repos/openaura/openaura/releases").mock(
            return_value=httpx.Response(200, json=load_fixture("github", "releases"))
        )

        async with httpx.AsyncClient(timeout=5) as client:
            connector = GitHubConnector(client, config, token="ghp_test")
            signals = await connector.fetch(since)

    assert len(signals.merged_prs) == 2
    assert {pr.author for pr in signals.merged_prs} == {"alice", "bob"}
    assert len(signals.closed_issues) == 1
    assert signals.closed_issues[0].title == "Timeout on long runs"
    assert len(signals.commits) == 2
    assert signals.commits[0].sha == "a1b2c3d"
    assert len(signals.open_blockers) == 1
    assert signals.open_blockers[0].label_or_tag == "blocker"
    assert len(signals.releases) == 1
    assert signals.releases[0].tag == "v0.1.0"
    assert signals.error_message is None


@pytest.mark.asyncio
async def test_github_fetch_safely_swallows_5xx():
    since = datetime(2026, 4, 16, 0, 0, 0, tzinfo=UTC)
    config = GitHubConfig(repo="openaura/openaura")

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(url__startswith="https://api.github.com/").mock(
            return_value=httpx.Response(500, text="boom")
        )
        async with httpx.AsyncClient(timeout=5) as client:
            connector = GitHubConnector(client, config, token="ghp_test")
            signals = await connector.fetch_safely(since)

    assert signals.error_message is not None
    assert signals.merged_prs == []
    assert signals.source == "github"


@pytest.mark.asyncio
async def test_github_from_config_missing_token():
    config = GitHubConfig(repo="o/r", token_env="NOPE")
    async with httpx.AsyncClient() as client:
        with pytest.raises(Exception) as exc:
            GitHubConnector.from_config(client, config, env={})
        assert "NOPE" in str(exc.value)
