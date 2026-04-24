# AURA Manifesto

OpenAURA is not a framework in the heavy sense. It is an update protocol: a small,
repeatable way for any repo to turn delivery signals into accurate project briefs.

The protocol exists so teams can stop translating work into status by hand. A repo
already contains the truth: pull requests, issues, commits, releases, builds, tickets,
metrics, and decisions. AURA reads those signals, keeps the claims grounded, and leaves a
clear weekly record in markdown.

## The 10 Rules

### 1. The repo is the source of truth

Every update should start from the systems where work actually happened. Prefer PRs,
issues, commits, releases, work items, pipeline runs, and declared metrics over memory,
meetings, or vibes.

### 2. Evidence beats narrative

Every meaningful claim needs a source. If a brief says something shipped, slipped,
blocked, improved, or regressed, it should point back to the signal that proves it.

### 3. Missing data is not zero

No signal means "unknown", not "nothing happened". AURA should distinguish between a
measured zero and missing coverage so readers know whether the project is quiet or the
instrumentation is thin.

### 4. Updates must be repeatable

The same repo, same configuration, and same time window should produce the same kind of
brief every run. AURA works because the ritual is small enough to survive every week.

### 5. Keep the brief human-sized

A good update is short enough to read and specific enough to act on. It should tell people
what changed, what matters, what is blocked, and what needs a decision without burying the
reader in raw logs.

### 6. Separate facts from recommendations

Findings describe what the signals show. Next focus describes what the team should do
about it. Mixing the two makes updates sound confident while hiding the reasoning.

### 7. Risks stay visible

Blockers, failed pipelines, stale PRs, and unresolved decisions belong in the brief even
when they are uncomfortable. AURA is accountable to delivery reality, not optics.

### 8. Shared metrics need local context

Every project can track common delivery measures, but each repo should declare what
"healthy" means for its own domain. A KPI without a local target is just decoration.

### 9. Markdown is the artifact

The update should live beside the work, in version control, as a durable project history.
Dashboards can help, but the canonical brief should be reviewable, diffable, and owned by
the repo.

### 10. Humans decide

AURA gathers, scores, summarizes, and recommends. It does not pretend to be the team. The
brief should make decisions easier by making the evidence clearer.

## What This Means For Every Repo

To follow the AURA Protocol, a project should keep these pieces close to the code:

- `aura.config.yml` to declare sources, cadence, and output.
- `aura.md` to describe the project, sprint focus, KPIs, targets, and local rules.
- `aura-docs/` to store generated briefs as a living history.
- Links back to source evidence for every risk, result, and recommendation.

Open method. Real signals. Weekly clarity.
