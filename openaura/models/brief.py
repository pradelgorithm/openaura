"""The final brief — the model summarizer emits and the output layer renders."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from openaura.models.kpis import Confidence, KPIScorecard

Severity = Literal["low", "medium", "high"]


class EvidenceLink(BaseModel):
    label: str
    url: HttpUrl
    source: str


class RiskItem(BaseModel):
    title: str
    description: str
    severity: Severity
    evidence: list[EvidenceLink] = Field(default_factory=list)


class Brief(BaseModel):
    project: str
    period_start: date
    period_end: date
    generated_at: datetime

    executive_summary: str
    sprint_activity: str
    kpi_scorecard: KPIScorecard
    findings: list[str] = Field(default_factory=list)
    risks_and_blockers: list[RiskItem] = Field(default_factory=list)
    decisions_needed: list[str] = Field(default_factory=list)
    next_focus: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)

    confidence: Confidence = "medium"
    connector_warnings: list[str] = Field(default_factory=list)
