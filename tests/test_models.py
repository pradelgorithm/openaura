"""Validation rules for the Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from openaura.models.config import (
    AuraConfig,
    AzureDevOpsConfig,
    GitHubConfig,
    OutputConfig,
    SignalsConfig,
)


def test_output_config_rejects_absolute_or_traversing_folder():
    with pytest.raises(ValidationError):
        OutputConfig(folder="/etc")
    with pytest.raises(ValidationError):
        OutputConfig(folder="../out")
    with pytest.raises(ValidationError):
        OutputConfig(folder="")


def test_output_config_default_is_aura_docs():
    assert OutputConfig().folder == "aura-docs"


def test_aura_config_requires_at_least_one_signal_source():
    with pytest.raises(ValidationError):
        AuraConfig(project="x", signals=SignalsConfig())


def test_github_repo_must_be_owner_slash_name():
    with pytest.raises(ValidationError):
        GitHubConfig(repo="no-slash")
    with pytest.raises(ValidationError):
        GitHubConfig(repo="o/")
    with pytest.raises(ValidationError):
        GitHubConfig(repo="/r")


def test_azuredevops_accepts_defaults():
    cfg = AzureDevOpsConfig()
    assert cfg.org_env == "AZURE_DEVOPS_ORG"
    assert cfg.token_env == "AZURE_DEVOPS_TOKEN"


def test_aura_config_defaults():
    cfg = AuraConfig(
        project="x",
        signals=SignalsConfig(github=GitHubConfig(repo="o/r")),
        output=OutputConfig(),
    )
    assert cfg.trigger == "weekly"
    assert cfg.model == "anthropic:claude-sonnet-4-6"
    assert "throughput" in cfg.kpis


def test_output_config_custom_folder():
    cfg = OutputConfig(folder="docs/reports")
    assert cfg.folder == "docs/reports"


def test_from_yaml_roundtrip(tmp_path):
    path = tmp_path / "c.yml"
    path.write_text(
        """
project: demo
signals:
  github:
    repo: owner/repo
output:
  folder: my-briefs
""".strip()
    )
    cfg = AuraConfig.from_yaml(path)
    assert cfg.project == "demo"
    assert cfg.signals.github is not None
    assert cfg.signals.github.repo == "owner/repo"
    assert cfg.output.folder == "my-briefs"


def test_from_yaml_defaults_output_when_absent(tmp_path):
    path = tmp_path / "c.yml"
    path.write_text(
        """
project: demo
signals:
  github:
    repo: owner/repo
""".strip()
    )
    cfg = AuraConfig.from_yaml(path)
    assert cfg.output.folder == "aura-docs"
