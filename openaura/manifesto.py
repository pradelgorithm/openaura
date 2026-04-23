"""Package access to the AURA Protocol manifesto."""

from __future__ import annotations

from importlib.resources import files


def load_manifesto() -> str:
    """Return the bundled AURA manifesto markdown."""
    return (files("openaura.instructions") / "manifesto.md").read_text(encoding="utf-8")


__all__ = ["load_manifesto"]
