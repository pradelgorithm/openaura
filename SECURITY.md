# Security Policy

## Supported versions

OpenAURA is pre-1.0. Only the latest minor release receives security patches.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |
| older   | ❌        |

## Reporting a vulnerability

**Do not open a public GitHub issue for security problems.** Instead, use:

**GitHub Security Advisory** (preferred, and currently the only channel):
[Report a vulnerability](https://github.com/pradelgorithm/openaura/security/advisories/new)

A dedicated disclosure email will be published here once the `openaura.org` domain is
live. Until then, please use the Security Advisory link above — it's private by
default and gives both parties an audit trail.

Please include:

- A description of the issue and the impact you expect.
- Steps to reproduce, or a proof-of-concept if available.
- The version / commit SHA you tested.
- Your disclosure preferences (coordinated vs. immediate).

## Response SLA

| Stage | Target |
|-------|--------|
| Initial acknowledgement | within 3 business days |
| Triage / severity assessment | within 7 business days |
| Fix released for critical / high | within 30 days of triage |
| Fix released for medium / low | within 90 days |

We publish a [GitHub Security Advisory](https://github.com/pradelgorithm/openaura/security/advisories)
once a fix ships, crediting the reporter unless anonymity is requested.

## Scope

**In scope**

- Code in this repository (the `openaura` Python package and shipped CI templates).
- Default configurations and documented use patterns.
- Supply-chain concerns (tampering with releases, build provenance).

**Out of scope**

- Vulnerabilities in upstream dependencies — please report those to the upstream project.
- Findings requiring a compromised local machine, physical access, or exfiltrated secrets.
- Denial-of-service against a user's own CI minutes budget via misconfigured schedules.

## Secrets handling expectations

OpenAURA runs in CI and reads signals from external APIs. It:

- Accepts secrets only from environment variables (never from config files).
- Never logs secret values; tokens are redacted in error messages.
- Refuses to send SMTP credentials over plaintext unless `AURA_ALLOW_INSECURE_SMTP=1`.
- Requires `https://` base URLs on all connector calls.

If you find a path where a secret leaks to logs, output briefs, or any third party,
that is **always in scope** and qualifies for a security advisory regardless of severity.

## Hardening this project ships with

- CodeQL scans on every push and PR.
- OpenSSF Scorecard runs weekly.
- Dependabot proposes dependency updates daily.
- Third-party GitHub Actions pinned to full commit SHAs.
- PyPI releases via Trusted Publishing (OIDC) with SLSA build provenance attestations.
- Sigstore signatures on release artifacts.
