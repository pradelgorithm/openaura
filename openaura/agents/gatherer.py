"""Gatherer subagent — pulls signals from every configured connector."""

from __future__ import annotations

import asyncio

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from openaura.agents._core import load_agent_instructions, model_ref
from openaura.agents.deps import AuraDeps
from openaura.connectors.azuredevops import AzureDevOpsConnector
from openaura.connectors.base import ConnectorError
from openaura.connectors.github import GitHubConnector
from openaura.models.signals import SignalsBundle, SignalSet

GATHER_PROMPT = (
    "Gather signals for the reporting period. Call every connector tool that is enabled "
    "in the config. Do not invent tools. Deduplicate by URL. Return the SignalsBundle."
)


def build_gatherer(model: str | Model) -> Agent[AuraDeps, SignalsBundle]:
    agent: Agent[AuraDeps, SignalsBundle] = Agent(
        model=model_ref(model),
        deps_type=AuraDeps,
        output_type=SignalsBundle,
        instructions=load_agent_instructions(),
        retries=2,
    )

    @agent.tool
    async def fetch_github(ctx: RunContext[AuraDeps]) -> SignalSet:
        """Fetch signals from GitHub. Returns an empty SignalSet with error_message on failure."""
        cfg = ctx.deps.config.signals.github
        if cfg is None:
            return SignalSet(source="github", error_message="github connector not configured")
        try:
            connector = GitHubConnector.from_config(ctx.deps.http, cfg, ctx.deps.env)
        except ConnectorError as exc:
            return SignalSet(source="github", error_message=str(exc))
        return await connector.fetch_safely(ctx.deps.period_start)

    @agent.tool
    async def fetch_azuredevops(ctx: RunContext[AuraDeps]) -> SignalSet:
        """Fetch signals from Azure DevOps. Degrades gracefully on failure."""
        cfg = ctx.deps.config.signals.azuredevops
        if cfg is None:
            return SignalSet(
                source="azuredevops", error_message="azuredevops connector not configured"
            )
        try:
            connector = AzureDevOpsConnector.from_config(ctx.deps.http, cfg, ctx.deps.env)
        except ConnectorError as exc:
            return SignalSet(source="azuredevops", error_message=str(exc))
        return await connector.fetch_safely(ctx.deps.period_start)

    return agent


async def gather_signals_direct(deps: AuraDeps) -> SignalsBundle:
    """Deterministic fan-out used when the LLM path isn't needed (tests, dry-run).

    The full pipeline uses ``build_gatherer().run(...)`` so the agent can reason about
    which sources to invoke; this function is a straight parallel call for speed.
    """
    tasks = []
    if deps.config.signals.github is not None:
        tasks.append(_safe_github(deps))
    if deps.config.signals.azuredevops is not None:
        tasks.append(_safe_ado(deps))
    results = await asyncio.gather(*tasks) if tasks else []
    return SignalsBundle(
        period_start=deps.period_start, period_end=deps.period_end, sets=list(results)
    )


async def _safe_github(deps: AuraDeps) -> SignalSet:
    cfg = deps.config.signals.github
    assert cfg is not None
    try:
        return await GitHubConnector.from_config(deps.http, cfg, deps.env).fetch_safely(
            deps.period_start
        )
    except ConnectorError as exc:
        return SignalSet(source="github", error_message=str(exc))


async def _safe_ado(deps: AuraDeps) -> SignalSet:
    cfg = deps.config.signals.azuredevops
    assert cfg is not None
    try:
        return await AzureDevOpsConnector.from_config(deps.http, cfg, deps.env).fetch_safely(
            deps.period_start
        )
    except ConnectorError as exc:
        return SignalSet(source="azuredevops", error_message=str(exc))
