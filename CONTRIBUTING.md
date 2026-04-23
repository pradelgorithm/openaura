# Contributing to OpenAURA

Thanks for your interest in contributing! OpenAURA is small and opinionated — the rules
below keep it that way.

## Ground rules

- **Evidence first.** The core agent rule (`openaura/instructions/aura.core.md`) is the
  soul of the project. Changes there require maintainer review and a written rationale
  in the PR description.
- **No raw LLM calls.** Every LLM interaction goes through Pydantic AI. PRs that add
  provider SDK calls like `anthropic.messages.create(...)` or `client.responses.create(...)`
  will be rejected.
- **No secrets in config.** Config files hold env var *names*, never values.
- **Graceful degradation.** A failing connector must produce a warning, never an exception.
- **Stateless.** No databases, no servers, no persistent processes.

## Development setup

```bash
git clone https://github.com/pradelgorithm/openaura.git
cd openaura
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Running the checks

Before opening a PR, run:

```bash
python -m ruff check .                              # lint
python -m ruff format --check .                     # formatting
python -m mypy openaura                             # type-check (strict)
python -m bandit -r openaura -ll                    # security lint
python -m pytest --cov=openaura --cov-fail-under=80 # tests + coverage
python -m pip_audit --skip-editable                 # dep CVE scan
```

CI runs the same checks on every PR; they must all pass before merge.

## Commit style

[Conventional Commits](https://www.conventionalcommits.org/). Examples:

- `feat: add slack output handler`
- `fix(connectors): retry GitHub 502 once`
- `docs: clarify on-merge trigger`
- `chore(deps): bump pydantic-ai`

## DCO sign-off

All commits must be signed off under the [Developer Certificate of Origin](https://developercertificate.org/):

```bash
git commit -s -m "feat: ..."
```

The CI enforces this.

## Signed commits

We also require GPG- or Sigstore-signed commits on `main`. Set up commit signing
[per GitHub's docs](https://docs.github.com/en/authentication/managing-commit-signature-verification).

## Pull request checklist

- [ ] Tests added or updated (coverage ≥ 80% retained)
- [ ] `ruff`, `mypy`, `bandit`, `pip-audit` all clean locally
- [ ] Commits signed off and signed
- [ ] Updated `CHANGELOG` entry if user-facing
- [ ] No new deps without a rationale in the PR description
- [ ] No changes to `aura.core.md` without maintainer sign-off

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). Do not file public issues for security problems.
