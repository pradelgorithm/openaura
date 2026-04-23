from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
import typer
from typer.testing import CliRunner

from openaura import load_manifesto
from openaura import main as cli
from openaura.models.brief import Brief
from openaura.models.config import AuraConfig, GitHubConfig, SignalsConfig
from openaura.models.kpis import KPIScorecard


def _config() -> AuraConfig:
    return AuraConfig(
        project="demo",
        signals=SignalsConfig(github=GitHubConfig(repo="o/r")),
    )


def _brief() -> Brief:
    return Brief(
        project="demo",
        period_start=date(2026, 4, 16),
        period_end=date(2026, 4, 23),
        generated_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        executive_summary="summary",
        sprint_activity="activity",
        kpi_scorecard=KPIScorecard(scores=[], overall_confidence="medium"),
        findings=[],
        risks_and_blockers=[],
        decisions_needed=[],
        next_focus=[],
        evidence=[],
    )


def test_resolve_trigger_uses_env_and_rejects_invalid_values():
    config = _config()

    assert cli._resolve_trigger(None, config, {"AURA_TRIGGER": "on-merge"}) == "on-merge"
    assert cli._resolve_trigger(None, config.model_copy(update={"trigger": "both"}), {}) == "weekly"

    with pytest.raises(typer.BadParameter):
        cli._resolve_trigger("daily", config, {})


def test_required_env_vars_includes_configured_tokens():
    assert cli._required_env_vars(_config()) == ["ANTHROPIC_API_KEY", "GITHUB_TOKEN"]


def test_required_env_vars_switches_to_openai_for_openai_models():
    config = _config().model_copy(update={"model": "openai:gpt-5.2"})

    assert cli._required_env_vars(config) == ["OPENAI_API_KEY", "GITHUB_TOKEN"]


def test_validate_command_reports_missing_config(tmp_path):
    runner = CliRunner()

    result = runner.invoke(cli.app, ["validate", "--config", str(tmp_path / "missing.yml")])

    assert result.exit_code == cli.EXIT_CONFIG
    assert "config file not found" in result.stderr


def test_validate_command_accepts_valid_config(tmp_path, monkeypatch):
    config_path = tmp_path / "aura.config.yml"
    config_path.write_text(
        "project: demo\nsignals:\n  github:\n    repo: o/r\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GITHUB_TOKEN", "test")
    runner = CliRunner()

    result = runner.invoke(cli.app, ["validate", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "config OK" in result.stdout


def test_manifesto_is_bundled_and_printable():
    runner = CliRunner()

    text = load_manifesto()
    result = runner.invoke(cli.app, ["manifesto"])

    assert "# AURA Manifesto" in text
    assert "The 10 Rules" in text
    assert result.exit_code == 0
    assert result.stdout == text


def test_run_command_dry_run_prints_brief_json(tmp_path, monkeypatch):
    config_path = tmp_path / "aura.config.yml"
    config_path.write_text(
        "project: demo\nsignals:\n  github:\n    repo: o/r\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GITHUB_TOKEN", "test")

    async def fake_run_aura(*args, **kwargs):
        return _brief()

    monkeypatch.setattr(cli, "run_aura", fake_run_aura)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["run", "--config", str(config_path), "--dry-run"])

    assert result.exit_code == 0
    assert '"project": "demo"' in result.stdout
