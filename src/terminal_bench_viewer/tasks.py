"""Load Terminal-Bench 2.0 tasks from a checkout of the benchmark repo."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# files larger than this are listed but not inlined
MAX_INLINE_BYTES = 200_000

SECTIONS = ("environment", "solution", "tests")
IGNORED = {".git", ".gitignore", ".DS_Store", "__pycache__"}


@dataclass
class TaskFile:
    path: str  # relative to the task dir
    size: int
    text: str | None  # None for binary or oversized files

    @property
    def section(self) -> str:
        top = self.path.split("/", 1)[0]
        return top if top in SECTIONS and "/" in self.path else "other"


@dataclass
class Task:
    name: str
    instruction: str
    readme: str | None
    description: str
    difficulty: str
    category: str
    tags: list[str]
    authors: list[str]
    expert_min: float | None
    junior_min: float | None
    agent_timeout_sec: float | None
    env: dict
    files: list[TaskFile] = field(default_factory=list)

    def files_in(self, section: str) -> list[TaskFile]:
        return [f for f in self.files if f.section == section]


def load_tasks(root: Path) -> list[Task]:
    """Load every task directory (one containing a task.toml) under root."""
    return [load_task(p.parent) for p in sorted(root.glob("*/task.toml"))]


def load_task(d: Path) -> Task:
    toml = tomllib.loads((d / "task.toml").read_text())
    meta, task = toml.get("metadata", {}), toml.get("task", {})
    readme = d / "README.md"

    authors = [a["name"] for a in task.get("authors", [])] or [
        meta.get("author_name", "unknown")
    ]
    tags = sorted({*meta.get("tags", []), *task.get("keywords", [])})

    return Task(
        name=d.name,
        instruction=(d / "instruction.md").read_text(),
        readme=readme.read_text() if readme.exists() else None,
        description=task.get("description", ""),
        difficulty=meta.get("difficulty", "unknown"),
        category=meta.get("category", "uncategorized"),
        tags=tags,
        authors=authors,
        expert_min=meta.get("expert_time_estimate_min"),
        junior_min=meta.get("junior_time_estimate_min"),
        agent_timeout_sec=toml.get("agent", {}).get("timeout_sec"),
        env=toml.get("environment", {}),
        files=list(_walk(d)),
    )


def _walk(d: Path):
    for p in sorted(d.rglob("*")):
        rel = p.relative_to(d)
        if not p.is_file() or IGNORED & set(rel.parts):
            continue
        yield TaskFile(rel.as_posix(), p.stat().st_size, _read_text(p))


def _read_text(p: Path) -> str | None:
    if p.stat().st_size > MAX_INLINE_BYTES:
        return None
    data = p.read_bytes()
    if b"\0" in data:
        return None
    try:
        return data.decode()
    except UnicodeDecodeError:
        return None
