"""Fetch per-task leaderboard results from Harbor Hub."""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

from harbor.auth.client import create_authenticated_client
from harbor.hub.leaderboards import LeaderboardClient

PAGE = 1000
CONCURRENCY = 8


@dataclass
class Cell:
    n: int = 0
    passed: float = 0.0  # sum of rewards

    @property
    def rate(self) -> float:
        return self.passed / self.n if self.n else 0.0


@dataclass
class Submission:
    id: str
    rank: int | None
    agent: str
    model: str
    effort: str | None
    accuracy: float  # official score, 0-100
    date: str | None
    agent_url: str | None
    model_url: str | None
    cells: dict[str, Cell] = field(default_factory=dict)  # task name -> cell

    @property
    def label(self) -> str:
        effort = f" ({self.effort})" if self.effort and self.effort != "none" else ""
        return f"{self.agent} · {self.model}{effort}"


def fetch_leaderboard(package: str, name: str) -> list[Submission]:
    """Fetch a public Hub leaderboard's rows and their per-task trial outcomes."""
    return asyncio.run(_fetch(package, name))


async def _fetch(package: str, name: str) -> list[Submission]:
    _, page = await LeaderboardClient().list_rows(
        package=package, name=name, page_size=PAGE
    )
    subs = {r.id: _submission(r.id, r.rank, r.metadata, r.metrics) for r in page.items}

    client = await create_authenticated_client()
    limit = asyncio.Semaphore(CONCURRENCY)

    async def fill(s: Submission) -> None:
        async with limit:
            trials = await _row_trials(client, s.id)
        for trial in trials:
            task = trial.get("task_name", "").rsplit("/", 1)[-1]
            cell = s.cells.setdefault(task, Cell())
            cell.n += 1
            # errored trials have no reward and count as failures
            cell.passed += (trial.get("rewards") or {}).get("reward") or 0.0

    await asyncio.gather(*(fill(s) for s in subs.values()))
    return sorted(subs.values(), key=lambda s: (s.rank or 1_000_000, -s.accuracy))


async def _row_trials(client, row_id: str) -> list[dict]:
    """Task name and rewards for every trial attached to a leaderboard row."""
    # trials attached to public rows are publicly readable; one query per row
    # keeps each statement well under the server's timeout
    trials: list[dict] = []
    while True:
        resp = await (
            client.table("leaderboard_row_trial")
            .select("trial:trial_id(task_name,rewards)")
            .eq("row_id", row_id)
            .order("trial_id")
            .range(len(trials), len(trials) + PAGE - 1)
            .execute()
        )
        trials += [t["trial"] or {} for t in resp.data]
        if len(resp.data) < PAGE:
            return trials


def _submission(id: str, rank: int | None, meta: dict, metrics: dict) -> Submission:
    agent, model = _display(meta.get("agent_display")), _display(
        meta.get("model_display")
    )
    return Submission(
        id=id,
        rank=rank,
        agent=agent[0] or meta.get("agent_name") or "unknown",
        model=model[0] or ", ".join(meta.get("model_names", [])) or "unknown",
        effort=meta.get("reasoning_effort"),
        accuracy=float(metrics.get("accuracy") or 0),
        date=meta.get("date"),
        agent_url=agent[1],
        model_url=model[1],
    )


def _display(v: dict | str | None) -> tuple[str | None, str | None]:
    """Normalize a display field, which is either a label or {label, url}."""
    if isinstance(v, dict):
        return v.get("label"), v.get("url")
    return v, None


def solve_rates(subs: list[Submission]) -> dict[str, float]:
    """Mean pass rate per task across all submissions."""
    totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    for s in subs:
        for task, c in s.cells.items():
            totals[task][0] += c.passed
            totals[task][1] += c.n
    return {t: p / n for t, (p, n) in totals.items() if n}
