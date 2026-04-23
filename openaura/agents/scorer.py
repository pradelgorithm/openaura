"""Scorer subagent — evaluates KPIs and emits a scorecard."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models import Model

from openaura.agents._core import load_agent_instructions, model_ref
from openaura.agents.deps import AuraDeps
from openaura.models.kpis import KPIScorecard
from openaura.models.signals import SignalsBundle


def build_scorer(model: str | Model) -> Agent[AuraDeps, KPIScorecard]:
    return Agent(
        model=model_ref(model),
        deps_type=AuraDeps,
        output_type=KPIScorecard,
        instructions=load_agent_instructions(),
        retries=2,
    )


def score_prompt(signals: SignalsBundle, kpis: list[str], project_context: str) -> str:
    bundle_json = signals.model_dump_json(indent=2)
    kpi_list = "\n".join(f"- {k}" for k in kpis) or "- (none defined)"
    return (
        "Score the configured KPIs against the signals below. Follow the Scorer rules in "
        "your instructions. Output a typed KPIScorecard.\n\n"
        "## KPIs to score\n"
        f"{kpi_list}\n\n"
        "## Project context (from aura.md)\n"
        f"{project_context or '(none provided)'}\n\n"
        "## Signals bundle\n"
        f"```json\n{bundle_json}\n```"
    )
