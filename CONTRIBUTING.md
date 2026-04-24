# Contributing to Open AURA

Thanks for your interest in contributing! Open AURA is small and opinionated — the rules
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

## AI-assisted contributions

AI-assisted and agentic development is allowed, but the human contributor is accountable
for the final contribution.

- Human review is required before merge for any agentic change.
- AI agents must not add `Signed-off-by` trailers. Only the human submitter may certify
  the DCO.
- Disclose substantial AI assistance in the PR body or with an `Assisted-by:` trailer,
  for example: `Assisted-by: Codex:gpt-5.4`.
- Review AI-generated content for correctness, tests, maintainability, security impact,
  and Apache-2.0 license compatibility before submitting.
- Do not submit generated code or docs that you cannot explain and maintain.
- If the change affects authentication, secrets, CI/CD, releases, dependencies,
  networking, file I/O, or bundled instructions, include a short security and license
  review note in the PR.

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
- [ ] AI-assisted changes disclosed and reviewed by a human for security and licensing
      impact

## Reporting security issues

See [`SECURITY.md`](SECURITY.md). Do not file public issues for security problems.
