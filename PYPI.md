# Open AURA

[![PyPI](https://img.shields.io/pypi/v/open-aura?logo=pypi&logoColor=white)](https://pypi.org/project/open-aura/)
[![Python](https://img.shields.io/pypi/pyversions/open-aura?logo=python&logoColor=white)](https://pypi.org/project/open-aura/)
[![CI](https://github.com/pradelgorithm/openaura/actions/workflows/ci.yml/badge.svg)](https://github.com/pradelgorithm/openaura/actions/workflows/ci.yml)
[![CodeQL](https://github.com/pradelgorithm/openaura/actions/workflows/codeql.yml/badge.svg)](https://github.com/pradelgorithm/openaura/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/pradelgorithm/openaura/badge)](https://securityscorecards.dev/viewer/?uri=github.com/pradelgorithm/openaura)
[![Coverage](https://codecov.io/gh/pradelgorithm/openaura/graph/badge.svg)](https://codecov.io/gh/pradelgorithm/openaura)
[![License](https://img.shields.io/badge/License-Apache_2.0-3b82f6.svg)](https://github.com/pradelgorithm/openaura/blob/main/LICENSE)

Open AURA is a CI-native Python CLI that generates recurring project briefs from
delivery signals and writes markdown reports into `aura-docs/`.

This page is the technical package reference. The human/product README lives in the
[GitHub repository](https://github.com/pradelgorithm/openaura#readme).

## Requirements

- Python 3.11 or newer
- A model provider key for Anthropic or OpenAI
- At least one signal connector, currently GitHub or Azure DevOps

The project CI verifies Python 3.11, 3.12, 3.13, and 3.14.

## Installation

```bash
python -m pip install open-aura
```

The package installs the `aura` console command.

## Configuration

Create `aura.config.yml` at the root of the repository where briefs should be written:

```yaml
project: "my-project"
trigger: weekly
schedule: "friday-5pm"
model: "anthropic:claude-sonnet-4-6"

signals:
  github:
    repo: "owner/repository"
    token_env: GITHUB_TOKEN
    default_branch: main

kpis:
  - throughput
  - cycle_time
  - blockers
  - bug_count

custom_kpis: []

output:
  folder: "aura-docs"
```

Supported `trigger` values are:

- `weekly`
- `on-merge`
- `both`

The `schedule` field is documentation for humans. The actual cron schedule belongs
in your CI workflow.

## Environment Variables

Open AURA reads secret values from environment variables. The config file stores only
the variable names.

| Purpose | Default variable |
|---|---|
| Anthropic models | `ANTHROPIC_API_KEY` |
| OpenAI models | `OPENAI_API_KEY` |
| GitHub connector | `GITHUB_TOKEN` |
| Azure DevOps org | `AZURE_DEVOPS_ORG` |
| Azure DevOps project | `AZURE_DEVOPS_PROJECT` |
| Azure DevOps token | `AZURE_DEVOPS_TOKEN` |

Model strings beginning with `anthropic:` require `ANTHROPIC_API_KEY`. Model strings
beginning with `openai:` require `OPENAI_API_KEY`.

## CLI

```bash
aura validate
aura run
aura run --dry-run
aura run --trigger on-merge
aura manifesto
```

`aura validate` checks the config and required environment variables without making
API or LLM calls.

`aura run` gathers signals, scores the project state, summarizes the brief, and writes
markdown to the configured output folder.

`aura run --dry-run` prints the structured brief JSON instead of writing a file.

## GitHub Actions

Install Open AURA in a workflow with pip:

```yaml
- uses: actions/setup-python@v6
  with:
    python-version: "3.13"

- run: python -m pip install open-aura
- run: aura validate
- run: aura run
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

The repository includes starter workflow templates for weekly, on-merge, and combined
trigger modes.

## Output

By default, briefs are written to:

```text
aura-docs/
```

Each brief is markdown, intended to be committed back to the same repository by CI.

## Links

- Source: https://github.com/pradelgorithm/openaura
- Issues: https://github.com/pradelgorithm/openaura/issues
- Security policy: https://github.com/pradelgorithm/openaura/blob/main/SECURITY.md
