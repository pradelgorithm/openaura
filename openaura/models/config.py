"""Configuration models loaded from ``aura.config.yml``."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class GitHubConfig(BaseModel):
    repo: str = Field(description="Owner/repo slug, e.g. 'openaura/openaura'.")
    token_env: str = "GITHUB_TOKEN"  # noqa: S105 - env var name, not a secret value
    default_branch: str = "main"

    @field_validator("repo")
    @classmethod
    def _validate_repo(cls, v: str) -> str:
        if v.count("/") != 1 or not all(v.split("/")):
            raise ValueError("repo must be of the form 'owner/name'")
        return v


class AzureDevOpsConfig(BaseModel):
    org_env: str = "AZURE_DEVOPS_ORG"
    project_env: str = "AZURE_DEVOPS_PROJECT"
    token_env: str = "AZURE_DEVOPS_TOKEN"  # noqa: S105 - env var name, not a secret value
    team: str | None = None
    repos: list[str] = Field(default_factory=list)


class SignalsConfig(BaseModel):
    github: GitHubConfig | None = None
    azuredevops: AzureDevOpsConfig | None = None

    @model_validator(mode="after")
    def _at_least_one_source(self) -> SignalsConfig:
        if self.github is None and self.azuredevops is None:
            raise ValueError("signals must enable at least one of: github, azuredevops")
        return self


class OutputConfig(BaseModel):
    """v0.1 output: a markdown brief committed to the repo under ``folder``."""

    folder: str = "aura-docs"

    @field_validator("folder")
    @classmethod
    def _validate_folder(cls, v: str) -> str:
        if not v or v.startswith("/") or ".." in v.split("/"):
            raise ValueError("folder must be a non-empty relative path without '..'")
        return v


Trigger = Literal["weekly", "on-merge", "both"]


class AuraConfig(BaseModel):
    project: str
    trigger: Trigger = "weekly"
    schedule: str = "friday-5pm"
    model: str = Field(
        default="anthropic:claude-sonnet-4-6",
        description=(
            "Pydantic AI model string, e.g. 'anthropic:claude-sonnet-4-6' "
            "or 'openai:gpt-5.2'. Bare names default to Anthropic."
        ),
    )
    signals: SignalsConfig
    kpis: list[str] = Field(
        default_factory=lambda: ["throughput", "cycle_time", "blockers", "bug_count"]
    )
    custom_kpis: list[str] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> AuraConfig:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise TypeError(f"{path} must contain a YAML mapping at its root")
        return cls.model_validate(data)
