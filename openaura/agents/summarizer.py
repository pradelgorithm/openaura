"""Summarizer subagent — writes each section of the brief."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.models import Model

from openaura.agents._core import load_agent_instructions, model_ref
from openaura.agents.deps import AuraDeps
from openaura.models.brief import Brief
from openaura.models.kpis import KPIScorecard
from openaura.models.signals import SignalsBundle


def build_summarizer(model: str | Model) -> Agent[AuraDeps, Brief]:
    return Agent(
        model=model_ref(model),
        deps_type=AuraDeps,
        output_type=Brief,
        instructions=load_agent_instructions(),
        retries=2,
    )


def summarize_prompt(
    project: str,
    signals: SignalsBundle,
    scorecard: KPIScorecard,
    project_context: str,
) -> str:
    return (
        f"Write the weekly brief for project '{project}'. Follow the Summarizer rules in "
        "your instructions exactly. Populate every field of the Brief schema. Empty "
        "lists get 'Nothing to report this period.' only where the schema expects prose "
        "— list fields may be empty lists.\n\n"
        "## Project context (from aura.md)\n"
        f"{project_context or '(none provided — use generic professional tone)'}\n\n"
        "## Period\n"
        f"- start: {signals.period_start.date().isoformat()}\n"
        f"- end: {signals.period_end.date().isoformat()}\n\n"
        "## KPI scorecard\n"
        f"```json\n{scorecard.model_dump_json(indent=2)}\n```\n\n"
        "## Signals bundle\n"
        f"```json\n{signals.model_dump_json(indent=2)}\n```"
    )
