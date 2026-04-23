"""Base connector interface and shared helpers."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

import httpx

from openaura.models.signals import SignalSet, SourceName

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    """Raised internally; caught by ``Connector.fetch_safely`` and mapped to SignalSet."""


class Connector(ABC):
    source: ClassVar[SourceName]

    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http

    @abstractmethod
    async def fetch(self, since: datetime) -> SignalSet:
        """Fetch signals for ``since`` onwards. Returns a populated ``SignalSet``."""

    async def fetch_safely(self, since: datetime) -> SignalSet:
        """Never raises. On any failure returns an empty SignalSet with error_message set.

        This is the entrypoint subagents should call so a failing connector degrades the
        brief instead of aborting the run.
        """
        try:
            return await self.fetch(since)
        except Exception as exc:
            logger.warning("connector %s failed: %s", self.source, _redact(str(exc)))
            return SignalSet(source=self.source, error_message=_redact(str(exc)))


def _redact(message: str) -> str:
    """Remove anything that could leak a bearer token from an error message."""
    # Strip Authorization header values and Basic/Bearer tokens.
    message = re.sub(r"(?i)(authorization[:=]\s*)\S+", r"\1***", message)
    message = re.sub(r"(?i)(bearer\s+)\S+", r"\1***", message)
    message = re.sub(r"(?i)(basic\s+)\S+", r"\1***", message)
    return message[:500]


def require_https(url: str) -> str:
    """Reject plain-http URLs — secrets must never ride plaintext."""
    if not url.startswith("https://"):
        raise ConnectorError(f"connector base URL must be https://, got: {url!r}")
    return url
