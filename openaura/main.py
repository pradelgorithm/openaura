"""Typer CLI entrypoint — ``aura run`` and ``aura validate``."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from openaura.agents._core import model_api_key_env_var
from openaura.agents.orchestrator import AuraRunError, run_aura
from openaura.manifesto import load_manifesto
from openaura.models.config import AuraConfig, Trigger
from openaura.output import markdown as md_out

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Open AURA — weekly briefs.")
log = logging.getLogger("openaura")

EXIT_CONFIG = 1
EXIT_ALL_CONNECTORS_FAILED = 2
EXIT_AGENT = 3


def _resolve_trigger(flag: str | None, config: AuraConfig, env: dict[str, str]) -> Trigger:
    value = flag or env.get("AURA_TRIGGER") or config.trigger
    if value == "both":
        return "weekly"  # on-merge CI workflow sets AURA_TRIGGER=on-merge explicitly
    if value not in {"weekly", "on-merge"}:
        raise typer.BadParameter(f"invalid trigger {value!r}")
    return value  # type: ignore[return-value]


def _load_config(path: Path) -> AuraConfig:
    if not path.is_file():
        raise typer.BadParameter(f"config file not found: {path}")
    try:
        return AuraConfig.from_yaml(path)
    except (TypeError, ValidationError, ValueError) as exc:
        raise typer.BadParameter(f"invalid config: {exc}") from exc


def _required_env_vars(config: AuraConfig) -> list[str]:
    names: list[str] = []
    model_key = model_api_key_env_var(config.model)
    if model_key is not None:
        names.append(model_key)
    if config.signals.github is not None:
        names.append(config.signals.github.token_env)
    if config.signals.azuredevops is not None:
        ado = config.signals.azuredevops
        names.extend([ado.org_env, ado.project_env, ado.token_env])
    return names


def _check_env(names: list[str], env: dict[str, str]) -> list[str]:
    return [name for name in names if not env.get(name)]


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", help="Path to aura.config.yml.")] = Path(
        "aura.config.yml"
    ),
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print the brief JSON; don't write to disk.")
    ] = False,
    trigger: Annotated[
        str | None, typer.Option("--trigger", help="Override trigger: weekly | on-merge.")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Debug logging.")] = False,
) -> None:
    """Run the full AURA pipeline and write the brief to the configured folder."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    env = dict(os.environ)
    try:
        cfg = _load_config(config)
        missing = _check_env(_required_env_vars(cfg), env)
        if missing:
            typer.secho(
                f"missing required env vars: {', '.join(missing)}",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(EXIT_CONFIG)
        active_trigger = _resolve_trigger(trigger, cfg, env)
        brief = asyncio.run(run_aura(cfg, active_trigger, Path.cwd(), env=env))
    except typer.BadParameter as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(EXIT_CONFIG) from exc
    except AuraRunError as exc:
        typer.secho(f"aura error ({exc.kind}): {exc.message}", fg=typer.colors.RED, err=True)
        raise typer.Exit(
            EXIT_ALL_CONNECTORS_FAILED if exc.kind == "all_connectors_failed" else EXIT_AGENT
        ) from exc

    if dry_run:
        sys.stdout.write(brief.model_dump_json(indent=2))
        sys.stdout.write("\n")
        raise typer.Exit(0)

    try:
        path = md_out.write(brief, Path.cwd(), folder=cfg.output.folder)
        typer.secho(f"wrote brief → {path}", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"delivery failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(EXIT_AGENT) from exc


@app.command()
def validate(
    config: Annotated[Path, typer.Option("--config", "-c", help="Path to aura.config.yml.")] = Path(
        "aura.config.yml"
    ),
) -> None:
    """Validate the config and that required env vars are present. No API calls."""
    env = dict(os.environ)
    try:
        cfg = _load_config(config)
    except typer.BadParameter as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(EXIT_CONFIG) from exc
    missing = _check_env(_required_env_vars(cfg), env)
    if missing:
        typer.secho(f"missing env vars: {', '.join(missing)}", fg=typer.colors.RED, err=True)
        raise typer.Exit(EXIT_CONFIG)
    typer.secho(
        f"config OK: project={cfg.project}, trigger={cfg.trigger}, folder={cfg.output.folder}",
        fg=typer.colors.GREEN,
    )


@app.command()
def manifesto() -> None:
    """Print the bundled AURA Protocol manifesto."""
    text = load_manifesto()
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    app()
