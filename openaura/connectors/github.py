"""GitHub REST connector — reads PRs, issues, commits, blockers, releases."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx

from openaura.connectors.base import Connector, ConnectorError, require_https
from openaura.models.config import GitHubConfig
from openaura.models.signals import (
    ClosedIssue,
    Commit,
    MergedPR,
    OpenBlocker,
    Release,
    SignalSet,
)

GITHUB_BASE_URL = "https://api.github.com"


class GitHubConnector(Connector):
    source = "github"

    def __init__(self, http: httpx.AsyncClient, config: GitHubConfig, token: str) -> None:
        super().__init__(http)
        self.config = config
        self.token = token
        self.base_url = require_https(GITHUB_BASE_URL)

    @classmethod
    def from_config(
        cls, http: httpx.AsyncClient, config: GitHubConfig, env: dict[str, str] | None = None
    ) -> GitHubConnector:
        env = env if env is not None else dict(os.environ)
        token = env.get(config.token_env)
        if not token:
            raise ConnectorError(f"missing env var {config.token_env!r} for GitHub connector")
        return cls(http, config, token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "openaura",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        response = await self.http.get(url, headers=self._headers(), params=params)
        response.raise_for_status()
        return response.json()

    async def _paginate(
        self, path: str, params: dict[str, Any] | None = None, max_pages: int = 10
    ) -> list[dict[str, Any]]:
        url: str | None = f"{self.base_url}{path}"
        query: dict[str, Any] | None = {"per_page": 100, **(params or {})}
        results: list[dict[str, Any]] = []
        pages = 0
        while url and pages < max_pages:
            response = await self.http.get(url, headers=self._headers(), params=query)
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, list):
                break
            results.extend(page)
            url = _next_link(response.headers.get("link"))
            query = None  # subsequent URLs already contain cursor params
            pages += 1
        return results

    async def fetch(self, since: datetime) -> SignalSet:
        since_iso = since.isoformat().replace("+00:00", "Z")
        signal_set = SignalSet(source="github")
        repo = self.config.repo

        raw_prs = await self._paginate(
            f"/repos/{repo}/pulls",
            {"state": "closed", "sort": "updated", "direction": "desc"},
        )
        for pr in raw_prs:
            merged_at = pr.get("merged_at")
            if not merged_at:
                continue
            merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
            if merged_dt < since:
                continue
            signal_set.merged_prs.append(
                MergedPR(
                    title=pr["title"],
                    author=(pr.get("user") or {}).get("login", "unknown"),
                    merged_at=merged_dt,
                    url=pr["html_url"],
                    labels=[lbl["name"] for lbl in pr.get("labels", [])],
                    source="github",
                )
            )

        raw_issues = await self._paginate(
            f"/repos/{repo}/issues",
            {"state": "closed", "since": since_iso},
        )
        for issue in raw_issues:
            if "pull_request" in issue:
                continue  # issues API returns PRs too — skip
            closed_at = issue.get("closed_at")
            if not closed_at:
                continue
            signal_set.closed_issues.append(
                ClosedIssue(
                    title=issue["title"],
                    labels=[lbl["name"] for lbl in issue.get("labels", [])],
                    closed_at=datetime.fromisoformat(closed_at.replace("Z", "+00:00")),
                    url=issue["html_url"],
                    assignee=((issue.get("assignee") or {}).get("login")),
                    source="github",
                )
            )

        raw_commits = await self._paginate(
            f"/repos/{repo}/commits",
            {"sha": self.config.default_branch, "since": since_iso},
        )
        for commit in raw_commits:
            commit_info = commit.get("commit") or {}
            author = (commit_info.get("author") or {}).get("name") or (
                (commit.get("author") or {}).get("login", "unknown")
            )
            ts = (commit_info.get("author") or {}).get("date")
            if not ts:
                continue
            signal_set.commits.append(
                Commit(
                    sha=commit["sha"][:7],
                    message=(commit_info.get("message") or "").splitlines()[0][:280],
                    author=author,
                    timestamp=datetime.fromisoformat(ts.replace("Z", "+00:00")),
                    url=commit["html_url"],
                    source="github",
                )
            )

        for label in ("blocker", "bug"):
            raw_open = await self._paginate(
                f"/repos/{repo}/issues",
                {"state": "open", "labels": label},
            )
            for issue in raw_open:
                if "pull_request" in issue:
                    continue
                created_at = issue.get("created_at")
                if not created_at:
                    continue
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age = (datetime.now(created_dt.tzinfo) - created_dt).days
                signal_set.open_blockers.append(
                    OpenBlocker(
                        title=issue["title"],
                        url=issue["html_url"],
                        created_at=created_dt,
                        age_days=age,
                        label_or_tag=label,
                        source="github",
                    )
                )

        raw_releases = await self._paginate(
            f"/repos/{repo}/releases", {"per_page": 30}, max_pages=1
        )
        for release in raw_releases:
            published = release.get("published_at")
            if not published:
                continue
            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if published_dt < since:
                continue
            signal_set.releases.append(
                Release(
                    tag=release["tag_name"],
                    name=release.get("name") or release["tag_name"],
                    published_at=published_dt,
                    url=release["html_url"],
                    source="github",
                )
            )

        return signal_set


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        segments = part.strip().split(";")
        if len(segments) < 2:
            continue
        url_segment = segments[0].strip()
        rel_segment = segments[1].strip()
        if (
            rel_segment == 'rel="next"'
            and url_segment.startswith("<")
            and url_segment.endswith(">")
        ):
            return url_segment[1:-1]
    return None
