"""Azure DevOps connector tests via respx."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import respx

from openaura.connectors.azuredevops import AzureDevOpsConnector
from openaura.models.config import AzureDevOpsConfig
from tests.conftest import load_fixture

BASE = "https://dev.azure.com/acme/demo"


@pytest.mark.asyncio
async def test_azuredevops_fetch_populates_all_sections():
    since = datetime(2026, 4, 16, 0, 0, 0, tzinfo=UTC)
    config = AzureDevOpsConfig(team="Demo Team", repos=["backend"])

    with respx.mock(assert_all_called=False) as respx_mock:
        wiql_calls = iter(
            [
                httpx.Response(200, json=load_fixture("azuredevops", "wiql_completed")),
                httpx.Response(200, json=load_fixture("azuredevops", "wiql_blocked")),
            ]
        )
        respx_mock.post(f"{BASE}/_apis/wit/wiql").mock(side_effect=lambda _r: next(wiql_calls))

        batch_calls = iter(
            [
                httpx.Response(200, json=load_fixture("azuredevops", "workitemsbatch_completed")),
                httpx.Response(200, json=load_fixture("azuredevops", "workitemsbatch_blocked")),
            ]
        )
        respx_mock.post(f"{BASE}/_apis/wit/workitemsbatch").mock(
            side_effect=lambda _r: next(batch_calls)
        )

        respx_mock.get(f"{BASE}/_apis/git/repositories/backend/pullrequests").mock(
            return_value=httpx.Response(200, json=load_fixture("azuredevops", "pullrequests"))
        )
        respx_mock.get(f"{BASE}/Demo Team/_apis/work/teamsettings/iterations").mock(
            return_value=httpx.Response(200, json=load_fixture("azuredevops", "iterations_current"))
        )
        respx_mock.get(
            f"{BASE}/Demo Team/_apis/work/teamsettings/iterations/iter-42/workitems"
        ).mock(
            return_value=httpx.Response(
                200, json=load_fixture("azuredevops", "iteration_workitems")
            )
        )
        respx_mock.get(f"{BASE}/_apis/pipelines").mock(
            return_value=httpx.Response(200, json=load_fixture("azuredevops", "pipelines"))
        )
        respx_mock.get(f"{BASE}/_apis/pipelines/5/runs").mock(
            return_value=httpx.Response(200, json=load_fixture("azuredevops", "pipeline_runs"))
        )

        async with httpx.AsyncClient(timeout=5) as client:
            connector = AzureDevOpsConnector(
                client, config, org="acme", project="demo", token="pat-xyz"
            )
            signals = await connector.fetch(since)

    assert len(signals.completed_work_items) == 2
    assert signals.completed_work_items[0].assigned_to == "Alice"
    assert len(signals.open_blockers) == 1
    assert signals.open_blockers[0].title.startswith("Waiting")
    assert len(signals.merged_prs) == 1
    assert signals.merged_prs[0].author == "Alice"
    assert signals.sprint_snapshot is not None
    assert signals.sprint_snapshot.sprint_name == "Sprint 42"
    assert signals.sprint_snapshot.committed_count == 3
    results = {run.result for run in signals.pipeline_runs}
    assert {"succeeded", "failed"}.issubset(results)


@pytest.mark.asyncio
async def test_azuredevops_fetch_safely_on_wiql_error():
    since = datetime(2026, 4, 16, 0, 0, 0, tzinfo=UTC)
    config = AzureDevOpsConfig()

    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.post(f"{BASE}/_apis/wit/wiql").mock(
            return_value=httpx.Response(401, text="unauthorized")
        )
        async with httpx.AsyncClient(timeout=5) as client:
            connector = AzureDevOpsConnector(
                client, config, org="acme", project="demo", token="pat-xyz"
            )
            signals = await connector.fetch_safely(since)

    assert signals.error_message is not None or signals.is_empty


@pytest.mark.asyncio
async def test_azuredevops_builds_basic_auth_header():
    config = AzureDevOpsConfig()
    async with httpx.AsyncClient() as client:
        connector = AzureDevOpsConnector(client, config, org="acme", project="demo", token="my-pat")
        headers = connector._headers()
    # base64(b":my-pat") == "Om15LXBhdA=="
    assert headers["Authorization"] == "Basic Om15LXBhdA=="
