"""Shared dependency container for all AURA subagents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from openaura.models.config import AuraConfig


@dataclass
class AuraDeps:
    config: AuraConfig
    project_context: str
    http: httpx.AsyncClient
    period_start: datetime
    period_end: datetime
    env: dict[str, str]
