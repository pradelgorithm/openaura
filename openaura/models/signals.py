"""Typed signal models — the contract between connectors and agents."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SourceName = Literal["github", "azuredevops"]


class MergedPR(BaseModel):
    title: str
    author: str
    merged_at: datetime
    url: HttpUrl
    labels: list[str] = Field(default_factory=list)
    source: SourceName


class ClosedIssue(BaseModel):
    title: str
    labels: list[str] = Field(default_factory=list)
    closed_at: datetime
    url: HttpUrl
    assignee: str | None = None
    source: SourceName


class Commit(BaseModel):
    sha: str = Field(description="Short 7-char SHA.")
    message: str
    author: str
    timestamp: datetime
    url: HttpUrl
    source: SourceName


class OpenBlocker(BaseModel):
    title: str
    url: HttpUrl
    created_at: datetime
    age_days: int
    label_or_tag: str
    source: SourceName


class Release(BaseModel):
    tag: str
    name: str
    published_at: datetime
    url: HttpUrl
    source: SourceName


class CompletedWorkItem(BaseModel):
    id: int
    title: str
    type: str
    completed_date: datetime
    assigned_to: str | None
    url: HttpUrl
    source: SourceName = "azuredevops"


class PipelineRun(BaseModel):
    pipeline_name: str
    result: Literal["succeeded", "failed", "canceled", "partiallySucceeded", "unknown"]
    finish_time: datetime
    url: HttpUrl
    source: SourceName = "azuredevops"


class SprintSnapshot(BaseModel):
    sprint_name: str
    committed_count: int
    completed_count: int
    remaining_count: int
    end_date: datetime | None
    source: SourceName = "azuredevops"


class SignalSet(BaseModel):
    """Everything one connector returned for the window."""

    source: SourceName
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None

    merged_prs: list[MergedPR] = Field(default_factory=list)
    closed_issues: list[ClosedIssue] = Field(default_factory=list)
    commits: list[Commit] = Field(default_factory=list)
    open_blockers: list[OpenBlocker] = Field(default_factory=list)
    releases: list[Release] = Field(default_factory=list)
    completed_work_items: list[CompletedWorkItem] = Field(default_factory=list)
    pipeline_runs: list[PipelineRun] = Field(default_factory=list)
    sprint_snapshot: SprintSnapshot | None = None

    @property
    def is_empty(self) -> bool:
        return not any(
            [
                self.merged_prs,
                self.closed_issues,
                self.commits,
                self.open_blockers,
                self.releases,
                self.completed_work_items,
                self.pipeline_runs,
                self.sprint_snapshot,
            ]
        )

    @property
    def degraded(self) -> bool:
        return self.error_message is not None


class SignalsBundle(BaseModel):
    """Signals from all connectors, deduplicated."""

    period_start: datetime
    period_end: datetime
    sets: list[SignalSet] = Field(default_factory=list)

    def by_source(self, source: SourceName) -> SignalSet | None:
        return next((s for s in self.sets if s.source == source), None)

    def warnings(self) -> list[str]:
        return [f"{s.source}: {s.error_message}" for s in self.sets if s.error_message is not None]

    @property
    def all_failed(self) -> bool:
        return bool(self.sets) and all(s.degraded or s.is_empty for s in self.sets)
