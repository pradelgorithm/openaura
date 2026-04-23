"""KPI scoring models — output of the scorer subagent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
Trend = Literal["up", "down", "flat", "no_signal"]


class KPIScore(BaseModel):
    name: str
    value: float | int | str | None = Field(
        description="Current measured value, or null if no signal."
    )
    target: float | int | str | None = Field(
        default=None, description="Target from aura.md if defined."
    )
    trend: Trend = "no_signal"
    confidence: Confidence
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="URLs or signal IDs supporting this score.",
    )
    note: str | None = Field(
        default=None,
        description="Short qualitative note — why trend/value, or 'no_signal' reason.",
    )


class KPIScorecard(BaseModel):
    scores: list[KPIScore]
    overall_confidence: Confidence
