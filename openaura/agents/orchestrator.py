"""Orchestrator — wires gatherer → scorer → summarizer into a Brief."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import httpx

from openaura.agents.deps import AuraDeps
from openaura.agents.gatherer import GATHER_PROMPT, build_gatherer, gather_signals_direct
from openaura.agents.scorer import build_scorer, score_prompt
from openaura.agents.summarizer import build_summarizer, summarize_prompt
from openaura.models.brief import Brief
from openaura.models.config import AuraConfig, Trigger
from openaura.models.signals import SignalsBundle

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 7
ON_MERGE_FALLBACK_HOURS = 24


class AuraRunError(RuntimeError):
    def __init__(self, kind: Literal["config", "all_connectors_failed", "agent"], message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


def compute_window(
    trigger: Trigger, cwd: Path, now: datetime | None = None
) -> tuple[datetime, datetime]:
    """Return (period_start, period_end) in UTC for the given trigger."""
    period_end = now or datetime.now(UTC)
    if trigger == "on-merge":
        anchor = _last_brief_anchor(cwd)
        period_start = anchor or (period_end - timedelta(hours=ON_MERGE_FALLBACK_HOURS))
    else:
        period_start = period_end - timedelta(days=DEFAULT_LOOKBACK_DAYS)
    return period_start, period_end


def _last_brief_anchor(cwd: Path) -> datetime | None:
    briefs = cwd / "output" / "briefs"
    if not briefs.is_dir():
        return None
    dated = sorted(briefs.glob("*.md"))
    if not dated:
        return None
    stem = dated[-1].stem
    try:
        return datetime.fromisoformat(stem).replace(tzinfo=UTC)
    except ValueError:
        return None


async def run_aura(
    config: AuraConfig,
    trigger: Trigger,
    cwd: Path,
    env: dict[str, str] | None = None,
    use_agent_gatherer: bool = True,
) -> Brief:
    """End-to-end pipeline. Raises AuraRunError on unrecoverable failures."""
    env_map = env if env is not None else dict(os.environ)
    period_start, period_end = compute_window(trigger, cwd)
    project_context = _read_project_context(cwd)

    async with httpx.AsyncClient(timeout=30) as http:
        deps = AuraDeps(
            config=config,
            project_context=project_context,
            http=http,
            period_start=period_start,
            period_end=period_end,
            env=env_map,
        )

        signals = await _run_gatherer(deps, use_agent_gatherer=use_agent_gatherer)

        if signals.all_failed:
            raise AuraRunError(
                "all_connectors_failed",
                "every configured connector returned empty or errored — no signals to summarize",
            )

        scorer = build_scorer(config.model)
        try:
            scorecard_result = await scorer.run(
                score_prompt(signals, config.kpis + config.custom_kpis, project_context),
                deps=deps,
            )
        except Exception as exc:
            raise AuraRunError("agent", f"scorer failed: {exc}") from exc
        scorecard = scorecard_result.output

        summarizer = build_summarizer(config.model)
        try:
            brief_result = await summarizer.run(
                summarize_prompt(config.project, signals, scorecard, project_context),
                deps=deps,
            )
        except Exception as exc:
            raise AuraRunError("agent", f"summarizer failed: {exc}") from exc
        brief = brief_result.output

    brief.connector_warnings = signals.warnings()
    brief.confidence = scorecard.overall_confidence
    brief.period_start = period_start.date()
    brief.period_end = period_end.date()
    brief.generated_at = datetime.now(UTC)
    brief.project = config.project
    brief.kpi_scorecard = scorecard
    return brief


async def _run_gatherer(deps: AuraDeps, use_agent_gatherer: bool) -> SignalsBundle:
    if not use_agent_gatherer:
        return await gather_signals_direct(deps)
    gatherer = build_gatherer(deps.config.model)
    try:
        result = await gatherer.run(GATHER_PROMPT, deps=deps)
    except Exception as exc:
        logger.warning("agent gatherer failed, falling back to direct fan-out: %s", exc)
        return await gather_signals_direct(deps)
    bundle = result.output
    bundle.period_start = deps.period_start
    bundle.period_end = deps.period_end
    return bundle


def _read_project_context(cwd: Path) -> str:
    path = cwd / "aura.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")
