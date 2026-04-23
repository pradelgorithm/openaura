from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from openaura.agents import orchestrator
from openaura.agents.deps import AuraDeps
from openaura.models.brief import Brief
from openaura.models.config import AuraConfig, GitHubConfig, SignalsConfig
from openaura.models.kpis import KPIScore, KPIScorecard
from openaura.models.signals import MergedPR, SignalsBundle, SignalSet


def _config() -> AuraConfig:
    return AuraConfig(
        project="demo",
        signals=SignalsConfig(github=GitHubConfig(repo="o/r")),
    )


def _signals(start: datetime, end: datetime) -> SignalsBundle:
    return SignalsBundle(
        period_start=start,
        period_end=end,
        sets=[
            SignalSet(
                source="github",
                merged_prs=[
                    MergedPR(
                        title="Ship CLI",
                        author="lucas",
                        merged_at=end,
                        url="https://github.com/o/r/pull/1",
                        labels=[],
                        source="github",
                    )
                ],
            ),
            SignalSet(source="github", error_message="rate limited"),
        ],
    )


def _scorecard() -> KPIScorecard:
    return KPIScorecard(
        scores=[KPIScore(name="throughput", value=1, trend="flat", confidence="high")],
        overall_confidence="high",
    )


def _brief() -> Brief:
    return Brief(
        project="placeholder",
        period_start=date(2000, 1, 1),
        period_end=date(2000, 1, 2),
        generated_at=datetime(2000, 1, 2, tzinfo=UTC),
        executive_summary="summary",
        sprint_activity="activity",
        kpi_scorecard=KPIScorecard(scores=[], overall_confidence="low"),
        findings=[],
        risks_and_blockers=[],
        decisions_needed=[],
        next_focus=[],
        evidence=[],
    )


class _FakeAgent:
    def __init__(self, output):
        self.output = output

    async def run(self, *args, **kwargs):
        return SimpleNamespace(output=self.output)


def test_compute_window_weekly_and_on_merge_anchor(tmp_path):
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    start, end = orchestrator.compute_window("weekly", tmp_path, now=now)
    assert end == now
    assert start == now - timedelta(days=orchestrator.DEFAULT_LOOKBACK_DAYS)

    briefs = tmp_path / "output" / "briefs"
    briefs.mkdir(parents=True)
    (briefs / "2026-04-22T10:00:00.md").write_text("brief", encoding="utf-8")
    start, _ = orchestrator.compute_window("on-merge", tmp_path, now=now)
    assert start == datetime(2026, 4, 22, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_run_gatherer_falls_back_to_direct(monkeypatch):
    start = datetime(2026, 4, 16, tzinfo=UTC)
    end = datetime(2026, 4, 23, tzinfo=UTC)
    deps = AuraDeps(
        config=_config(),
        project_context="",
        http=httpx.AsyncClient(),
        period_start=start,
        period_end=end,
        env={},
    )

    class BrokenAgent:
        async def run(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def fake_direct(received_deps):
        assert received_deps is deps
        return _signals(start, end)

    monkeypatch.setattr(orchestrator, "build_gatherer", lambda model: BrokenAgent())
    monkeypatch.setattr(orchestrator, "gather_signals_direct", fake_direct)

    try:
        bundle = await orchestrator._run_gatherer(deps, use_agent_gatherer=True)
    finally:
        await deps.http.aclose()

    assert bundle.by_source("github") is not None


@pytest.mark.asyncio
async def test_run_aura_direct_pipeline_rewrites_brief_metadata(tmp_path, monkeypatch):
    (tmp_path / "aura.md").write_text("context", encoding="utf-8")
    start = datetime.now(UTC) - timedelta(days=7)
    end = datetime.now(UTC)

    async def fake_direct(deps):
        return _signals(start, end)

    monkeypatch.setattr(orchestrator, "gather_signals_direct", fake_direct)
    monkeypatch.setattr(orchestrator, "build_scorer", lambda model: _FakeAgent(_scorecard()))
    monkeypatch.setattr(orchestrator, "build_summarizer", lambda model: _FakeAgent(_brief()))

    brief = await orchestrator.run_aura(
        _config(),
        "weekly",
        tmp_path,
        env={"GITHUB_TOKEN": "x"},
        use_agent_gatherer=False,
    )

    assert brief.project == "demo"
    assert brief.confidence == "high"
    assert brief.kpi_scorecard.overall_confidence == "high"
    assert brief.connector_warnings == ["github: rate limited"]


@pytest.mark.asyncio
async def test_run_aura_raises_when_every_connector_failed(tmp_path, monkeypatch):
    async def failed_direct(deps):
        return SignalsBundle(
            period_start=deps.period_start,
            period_end=deps.period_end,
            sets=[SignalSet(source="github", error_message="nope")],
        )

    monkeypatch.setattr(orchestrator, "gather_signals_direct", failed_direct)

    with pytest.raises(orchestrator.AuraRunError) as exc:
        await orchestrator.run_aura(
            _config(),
            "weekly",
            tmp_path,
            env={},
            use_agent_gatherer=False,
        )

    assert exc.value.kind == "all_connectors_failed"
