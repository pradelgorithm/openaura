"""Render a Brief to a timestamped markdown file under the configured folder."""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from openaura.models.brief import Brief


@lru_cache(maxsize=1)
def _template_src() -> str:
    return (files("openaura.output.templates") / "brief.md.j2").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _env() -> Environment:
    return Environment(
        autoescape=False,  # nosec B701  # noqa: S701 - markdown output, not HTML
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )


def render(brief: Brief) -> str:
    return _env().from_string(_template_src()).render(**brief.model_dump(mode="json"))


def filename(brief: Brief) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", brief.project.lower()).strip("-") or "project"
    return f"{brief.period_end.isoformat()}-{slug}-brief.md"


def write(brief: Brief, cwd: Path, folder: str = "aura-docs") -> Path:
    docs_dir = cwd / folder
    docs_dir.mkdir(parents=True, exist_ok=True)
    path = docs_dir / filename(brief)
    path.write_text(render(brief), encoding="utf-8")
    return path
