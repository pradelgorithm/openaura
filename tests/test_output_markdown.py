from __future__ import annotations

from datetime import UTC, date, datetime

from openaura.models.brief import Brief
from openaura.models.kpis import KPIScorecard
from openaura.output import markdown


def _brief(project: str = "Demo Project!") -> Brief:
    return Brief(
        project=project,
        period_start=date(2026, 4, 16),
        period_end=date(2026, 4, 23),
        generated_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        executive_summary="summary",
        sprint_activity="activity",
        kpi_scorecard=KPIScorecard(scores=[], overall_confidence="medium"),
        findings=["finding"],
        risks_and_blockers=[],
        decisions_needed=[],
        next_focus=[],
        evidence=[],
    )


def test_filename_slugifies_project_name():
    assert markdown.filename(_brief()) == "2026-04-23-demo-project-brief.md"
    assert markdown.filename(_brief("!!!")) == "2026-04-23-project-brief.md"


def test_render_and_write_markdown(tmp_path):
    brief = _brief()

    rendered = markdown.render(brief)
    assert "Demo Project!" in rendered
    assert "summary" in rendered

    path = markdown.write(brief, tmp_path, folder="docs")
    assert path == tmp_path / "docs" / "2026-04-23-demo-project-brief.md"
    assert path.read_text(encoding="utf-8") == rendered
