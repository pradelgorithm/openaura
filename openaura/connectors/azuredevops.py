"""Azure DevOps REST connector — work items, PRs, pipelines, sprint snapshot."""

from __future__ import annotations

import base64
import os
from datetime import datetime
from typing import Any, cast

import httpx

from openaura.connectors.base import Connector, ConnectorError, require_https
from openaura.models.config import AzureDevOpsConfig
from openaura.models.signals import (
    CompletedWorkItem,
    MergedPR,
    OpenBlocker,
    PipelineRun,
    SignalSet,
    SprintSnapshot,
)

API_VERSION = "7.1"


class AzureDevOpsConnector(Connector):
    source = "azuredevops"

    def __init__(
        self,
        http: httpx.AsyncClient,
        config: AzureDevOpsConfig,
        org: str,
        project: str,
        token: str,
    ) -> None:
        super().__init__(http)
        self.config = config
        self.org = org
        self.project = project
        self.token = token
        self.base_url = require_https(f"https://dev.azure.com/{org}/{project}")

    @classmethod
    def from_config(
        cls,
        http: httpx.AsyncClient,
        config: AzureDevOpsConfig,
        env: dict[str, str] | None = None,
    ) -> AzureDevOpsConnector:
        env = env if env is not None else dict(os.environ)
        org = env.get(config.org_env)
        project = env.get(config.project_env)
        token = env.get(config.token_env)
        if not org or not project or not token:
            missing = [
                name
                for name, val in (
                    (config.org_env, org),
                    (config.project_env, project),
                    (config.token_env, token),
                )
                if not val
            ]
            raise ConnectorError(
                f"missing env vars for Azure DevOps connector: {', '.join(missing)}"
            )
        return cls(http, config, org, project, token)

    def _headers(self) -> dict[str, str]:
        encoded = base64.b64encode(b":" + self.token.encode("utf-8")).decode("ascii")
        return {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
            "User-Agent": "openaura",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = {"api-version": API_VERSION, **(params or {})}
        url = f"{self.base_url}{path}"
        response = await self.http.get(url, headers=self._headers(), params=query)
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        query = {"api-version": API_VERSION}
        url = f"{self.base_url}{path}"
        response = await self.http.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            params=query,
            json=body,
        )
        response.raise_for_status()
        return response.json()

    async def fetch(self, since: datetime) -> SignalSet:
        signal_set = SignalSet(source="azuredevops")
        project = _wiql_string(self.project)

        # ── Completed work items via WIQL ──────────────────────────────────────
        days = max(1, (datetime.now(since.tzinfo) - since).days or 1)
        wiql = {
            "query": (
                "SELECT [System.Id], [System.Title], [System.WorkItemType], "  # nosec B608  # noqa: S608
                "[System.AssignedTo], [System.ChangedDate] "
                "FROM WorkItems "
                f"WHERE [System.TeamProject] = '{project}' "
                "AND [System.State] IN ('Done', 'Closed', 'Resolved') "
                f"AND [System.ChangedDate] >= @Today-{days} "
                "ORDER BY [System.ChangedDate] DESC"
            )
        }
        try:
            wiql_result = await self._post("/_apis/wit/wiql", wiql)
            ids = [item["id"] for item in wiql_result.get("workItems", [])][:200]
            if ids:
                batch = await self._post(
                    "/_apis/wit/workitemsbatch",
                    {
                        "ids": ids,
                        "fields": [
                            "System.Id",
                            "System.Title",
                            "System.WorkItemType",
                            "System.AssignedTo",
                            "System.ChangedDate",
                        ],
                    },
                )
                for wi in batch.get("value", []):
                    fields = wi.get("fields", {})
                    changed = fields.get("System.ChangedDate")
                    if not changed:
                        continue
                    assigned = fields.get("System.AssignedTo")
                    if isinstance(assigned, dict):
                        assigned_name = assigned.get("displayName")
                    else:
                        assigned_name = assigned
                    signal_set.completed_work_items.append(
                        CompletedWorkItem(
                            id=int(fields["System.Id"]),
                            title=fields.get("System.Title", ""),
                            type=fields.get("System.WorkItemType", "WorkItem"),
                            completed_date=datetime.fromisoformat(changed.replace("Z", "+00:00")),
                            assigned_to=assigned_name,
                            url=_wi_url(self.org, self.project, int(fields["System.Id"])),
                        )
                    )
        except httpx.HTTPError as exc:
            signal_set.error_message = f"wiql: {exc}"
            return signal_set

        # ── Blocked items ──────────────────────────────────────────────────────
        blocked_wiql = {
            "query": (
                "SELECT [System.Id], [System.Title], [System.CreatedDate] "  # nosec B608  # noqa: S608
                "FROM WorkItems "
                f"WHERE [System.TeamProject] = '{project}' "
                "AND [System.Tags] CONTAINS 'Blocked' "
                "AND [System.State] <> 'Closed'"
            )
        }
        try:
            blocked_result = await self._post("/_apis/wit/wiql", blocked_wiql)
            blocked_ids = [item["id"] for item in blocked_result.get("workItems", [])][:100]
            if blocked_ids:
                blocked_batch = await self._post(
                    "/_apis/wit/workitemsbatch",
                    {
                        "ids": blocked_ids,
                        "fields": ["System.Id", "System.Title", "System.CreatedDate"],
                    },
                )
                for wi in blocked_batch.get("value", []):
                    fields = wi.get("fields", {})
                    created = fields.get("System.CreatedDate")
                    if not created:
                        continue
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    age = (datetime.now(created_dt.tzinfo) - created_dt).days
                    signal_set.open_blockers.append(
                        OpenBlocker(
                            title=fields.get("System.Title", ""),
                            url=_wi_url(self.org, self.project, int(fields["System.Id"])),
                            created_at=created_dt,
                            age_days=age,
                            label_or_tag="Blocked",
                            source="azuredevops",
                        )
                    )
        except httpx.HTTPError:
            pass  # blocker query is optional — don't degrade the whole set

        # ── Completed PRs across configured repos ──────────────────────────────
        for repo_id in self.config.repos:
            try:
                prs = await self._get(
                    f"/_apis/git/repositories/{repo_id}/pullrequests",
                    {
                        "searchCriteria.status": "completed",
                        "searchCriteria.minTime": since.isoformat(),
                        "$top": 100,
                    },
                )
                for pr in prs.get("value", []):
                    closed = pr.get("closedDate")
                    if not closed:
                        continue
                    closed_dt = datetime.fromisoformat(closed.replace("Z", "+00:00"))
                    if closed_dt < since:
                        continue
                    signal_set.merged_prs.append(
                        MergedPR(
                            title=pr.get("title", ""),
                            author=((pr.get("createdBy") or {}).get("displayName", "unknown")),
                            merged_at=closed_dt,
                            url=_pr_url(self.org, self.project, repo_id, pr["pullRequestId"]),
                            labels=[lbl.get("name", "") for lbl in pr.get("labels", [])],
                            source="azuredevops",
                        )
                    )
            except httpx.HTTPError:
                continue

        # ── Current iteration (sprint snapshot) ────────────────────────────────
        team = self.config.team
        try:
            iterations_path = (
                f"/{team}/_apis/work/teamsettings/iterations"
                if team
                else "/_apis/work/teamsettings/iterations"
            )
            iterations = await self._get(iterations_path, {"$timeframe": "current"})
            current = (iterations.get("value") or [None])[0]
            if current:
                iter_id = current["id"]
                iter_items_path = (
                    f"/{team}/_apis/work/teamsettings/iterations/{iter_id}/workitems"
                    if team
                    else f"/_apis/work/teamsettings/iterations/{iter_id}/workitems"
                )
                iter_items = await self._get(iter_items_path)
                work_items = iter_items.get("workItemRelations") or []
                committed = len(work_items)
                completed = sum(
                    1 for wi in signal_set.completed_work_items if wi.completed_date >= since
                )
                end_str = (current.get("attributes") or {}).get("finishDate")
                signal_set.sprint_snapshot = SprintSnapshot(
                    sprint_name=current.get("name", "current"),
                    committed_count=committed,
                    completed_count=completed,
                    remaining_count=max(0, committed - completed),
                    end_date=(
                        datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else None
                    ),
                )
        except httpx.HTTPError:
            pass

        # ── Pipeline runs (last 7d) ───────────────────────────────────────────
        try:
            pipelines = await self._get("/_apis/pipelines", {"$top": 50})
            for pipeline in pipelines.get("value", []):
                pid = pipeline["id"]
                runs = await self._get(f"/_apis/pipelines/{pid}/runs", {"$top": 20})
                for run in runs.get("value", []):
                    finish = run.get("finishedDate")
                    if not finish:
                        continue
                    finish_dt = datetime.fromisoformat(finish.replace("Z", "+00:00"))
                    if finish_dt < since:
                        continue
                    result = cast(str, run.get("result") or "unknown")
                    signal_set.pipeline_runs.append(
                        PipelineRun(
                            pipeline_name=pipeline.get("name", f"pipeline-{pid}"),
                            result=result if result in _PIPELINE_RESULTS else "unknown",
                            finish_time=finish_dt,
                            url=(run.get("_links", {}).get("web", {}).get("href"))
                            or f"https://dev.azure.com/{self.org}/{self.project}/_build/results?buildId={run['id']}",
                        )
                    )
        except httpx.HTTPError:
            pass

        return signal_set


_PIPELINE_RESULTS = {"succeeded", "failed", "canceled", "partiallySucceeded", "unknown"}


def _wi_url(org: str, project: str, wid: int) -> str:
    return f"https://dev.azure.com/{org}/{project}/_workitems/edit/{wid}"


def _pr_url(org: str, project: str, repo: str, pr_id: int) -> str:
    return f"https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{pr_id}"


def _wiql_string(value: str) -> str:
    return value.replace("'", "''")
