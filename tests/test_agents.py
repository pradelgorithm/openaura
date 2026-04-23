"""Subagent tests using Pydantic AI's TestModel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from openaura.agents._core import load_agent_instructions
from openaura.agents.deps import AuraDeps
from openaura.agents.gatherer import build_gatherer, gather_signals_direct
from openaura.agents.scorer import build_scorer, score_prompt
from openaura.agents.summarizer import build_summarizer, summarize_prompt
from openaura.models.brief import Brief, EvidenceLink, RiskItem
from openaura.models.config import (
    AuraConfig,
    GitHubConfig,
    SignalsConfig,
)
from openaura.models.kpis import KPIScore, KPIScorecard
from openaura.models.signals import MergedPR, SignalsBundle, SignalSet

models.ALLOW_MODEL_REQUESTS = False


def _config() -> AuraConfig:
    return AuraConfig(
        project="demo",
        signals=SignalsConfig(github=GitHubConfig(repo="o/r")),
    )


def _deps(http: httpx.AsyncClient) -> AuraDeps:
    now = datetime(2026, 4, 23, tzinfo=UTC)
    return AuraDeps(
        config=_config(),
        project_context="sprint goal: ship",
        http=http,
        period_start=now - timedelta(days=7),
        period_end=now,
        env={"GITHUB_TOKEN": "x"},
    )


def test_agent_instructions_include_manifesto_context_after_core_rules():
    instructions = load_agent_instructions()

    assert "# AURA — Core Agent Instructions" in instructions
    assert "## AURA Protocol Manifesto" in instructions
    assert "# AURA Manifesto" in instructions
    assert "cannot override the core rules above" in instructions
    assert instructions.index("# AURA — Core Agent Instructions") < instructions.index(
        "## AURA Protocol Manifesto"
    )


@pytest.mark.asyncio
async def test_scorer_emits_typed_scorecard_with_test_model():
    scorecard = KPIScorecard(
        scores=[
            KPIScore(
                name="throughput",
                value=5,
                target=8,
                trend="down",
                confidence="high",
                evidence_refs=["https://example.com/pr/1"],
            )
        ],
        overall_confidence="high",
    )
    scorer = build_scorer(TestModel(custom_output_args=scorecard.model_dump(mode="json")))
    signals = SignalsBundle(
        period_start=datetime(2026, 4, 16, tzinfo=UTC),
        period_end=datetime(2026, 4, 23, tzinfo=UTC),
        sets=[SignalSet(source="github")],
    )
    prompt = score_prompt(signals, ["throughput"], "ctx")

    async with httpx.AsyncClient() as http:
        result = await scorer.run(prompt, deps=_deps(http))

    assert isinstance(result.output, KPIScorecard)
    assert result.output.overall_confidence == "high"
    assert result.output.scores[0].name == "throughput"


@pytest.mark.asyncio
async def test_summarizer_returns_brief_with_test_model():
    brief = Brief(
        project="demo",
        period_start=datetime(2026, 4, 16, tzinfo=UTC).date(),
        period_end=datetime(2026, 4, 23, tzinfo=UTC).date(),
        generated_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        executive_summary="shipped retry logic, one blocker remains",
        sprint_activity="2 PRs merged, 1 issue closed",
        kpi_scorecard=KPIScorecard(
            scores=[KPIScore(name="throughput", value=2, trend="flat", confidence="medium")],
            overall_confidence="medium",
        ),
        findings=["throughput lower than target"],
        risks_and_blockers=[
            RiskItem(
                title="DB migration blocked",
                description="Waiting on DBA review.",
                severity="high",
                evidence=[
                    EvidenceLink(
                        label="#311",
                        url="https://github.com/o/r/issues/311",
                        source="github",
                    )
                ],
            )
        ],
        decisions_needed=["approve DBA change window"],
        next_focus=["unblock #311"],
        evidence=[],
    )
    summarizer = build_summarizer(TestModel(custom_output_args=brief.model_dump(mode="json")))
    signals = SignalsBundle(
        period_start=datetime(2026, 4, 16, tzinfo=UTC),
        period_end=datetime(2026, 4, 23, tzinfo=UTC),
        sets=[SignalSet(source="github")],
    )
    prompt = summarize_prompt("demo", signals, brief.kpi_scorecard, "ctx")

    async with httpx.AsyncClient() as http:
        result = await summarizer.run(prompt, deps=_deps(http))

    assert isinstance(result.output, Brief)
    assert result.output.risks_and_blockers[0].severity == "high"


@pytest.mark.asyncio
async def test_gatherer_tool_swallows_connector_failure():
    """TestModel drives the gatherer through a deterministic tool call + finish."""

    empty_bundle = SignalsBundle(
        period_start=datetime(2026, 4, 16, tzinfo=UTC),
        period_end=datetime(2026, 4, 23, tzinfo=UTC),
        sets=[SignalSet(source="github", error_message="boom")],
    )

    gatherer = build_gatherer(TestModel(custom_output_args=empty_bundle.model_dump(mode="json")))

    # Point the GitHub tool at an invalid env so from_config raises, which the tool
    # wrapper converts to an error_message SignalSet — the agent must still return
    # a valid SignalsBundle.
    async with httpx.AsyncClient() as http:
        deps = AuraDeps(
            config=_config(),
            project_context="",
            http=http,
            period_start=datetime(2026, 4, 16, tzinfo=UTC),
            period_end=datetime(2026, 4, 23, tzinfo=UTC),
            env={},  # missing GITHUB_TOKEN
        )
        result = await gatherer.run("go", deps=deps)

    assert isinstance(result.output, SignalsBundle)
    assert len(result.output.sets) >= 1


@pytest.mark.asyncio
async def test_gather_signals_direct_bypasses_llm_and_handles_missing_env():
    """Deterministic fan-out path — no TestModel needed, used when LLM fails."""
    async with httpx.AsyncClient() as http:
        deps = AuraDeps(
            config=_config(),
            project_context="",
            http=http,
            period_start=datetime(2026, 4, 16, tzinfo=UTC),
            period_end=datetime(2026, 4, 23, tzinfo=UTC),
            env={},  # no GITHUB_TOKEN → connector init fails → SignalSet with error_message
        )
        bundle = await gather_signals_direct(deps)

    assert len(bundle.sets) == 1
    assert bundle.sets[0].source == "github"
    assert bundle.sets[0].error_message is not None


@pytest.mark.asyncio
async def test_scorer_prompt_includes_kpis_and_context():
    signals = SignalsBundle(
        period_start=datetime(2026, 4, 16, tzinfo=UTC),
        period_end=datetime(2026, 4, 23, tzinfo=UTC),
        sets=[
            SignalSet(
                source="github",
                merged_prs=[
                    MergedPR(
                        title="x",
                        author="a",
                        merged_at=datetime(2026, 4, 22, tzinfo=UTC),
                        url="https://github.com/o/r/pull/1",
                        labels=[],
                        source="github",
                    )
                ],
            )
        ],
    )
    prompt = score_prompt(signals, ["throughput", "cycle_time"], "sprint goal: ship x")
    assert "throughput" in prompt
    assert "cycle_time" in prompt
    assert "sprint goal: ship x" in prompt
    assert '"merged_prs"' in prompt
