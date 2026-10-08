"""Load Terminal-Bench tasks (Harbor task format) from a directory."""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# files larger than this are listed but not inlined
MAX_INLINE_BYTES = 200_000

SECTIONS = ("environment", "solution", "tests")
IGNORED = {".git", ".gitignore", ".DS_Store", "__pycache__"}

# free-text metadata fields some tasks carry, shown on the task page
NOTES = {
    "difficulty_explanation": "Why it's hard",
    "solution_explanation": "Solution approach",
    "verification_explanation": "Verification",
    "relevant_experience": "Relevant experience",
}


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
    difficulty: str | None
    category: str
    subcategory: str | None
    tags: list[str]
    authors: list[str]
    expert_min: float | None
    junior_min: float | None
    agent_timeout_sec: float | None
    env: dict
    notes: dict[str, str] = field(default_factory=dict)
    files: list[TaskFile] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """Description, or the start of the instruction if there is none."""
        return self.description or _summary(self.instruction)

    def files_in(self, section: str) -> list[TaskFile]:
        return [f for f in self.files if f.section == section]


def load_tasks(root: Path) -> list[Task]:
    """Load every task directory (one containing a task.toml) under root."""
    return [load_task(p.parent) for p in sorted(root.glob("*/task.toml"))]


def load_task(d: Path) -> Task:
    toml = tomllib.loads((d / "task.toml").read_text())
    meta, task = toml.get("metadata", {}), toml.get("task", {})
    instruction = (d / "instruction.md").read_text()
    readme = d / "README.md"

    authors = [a["name"] for a in task.get("authors", [])] or _as_list(
        meta.get("author_name", "unknown")
    )
    tags = sorted({*meta.get("tags", []), *task.get("keywords", [])})

    # 2.0 estimates in minutes, later versions in hours
    expert = meta.get("expert_time_estimate_min")
    if expert is None and "expert_time_estimate_hours" in meta:
        expert = meta["expert_time_estimate_hours"] * 60

    return Task(
        name=d.name,
        instruction=instruction,
        readme=readme.read_text() if readme.exists() else None,
        description=task.get("description", ""),
        difficulty=meta.get("difficulty"),
        category=meta.get("category", "uncategorized"),
        subcategory=meta.get("subcategory"),
        tags=tags,
        authors=authors,
        expert_min=expert,
        junior_min=meta.get("junior_time_estimate_min"),
        agent_timeout_sec=toml.get("agent", {}).get("timeout_sec"),
        env=toml.get("environment", {}),
        notes={v: meta[k] for k, v in NOTES.items() if meta.get(k)},
        files=list(_walk(d)),
    )


def _as_list(v: str | list[str]) -> list[str]:
    return v if isinstance(v, list) else [v]


def strip_comments(md: str) -> str:
    return re.sub(r"<!--.*?-->", "", md, flags=re.S)


def _summary(md: str, limit: int = 200) -> str:
    """First paragraph of markdown as plain text, truncated."""
    para = next((p for p in strip_comments(md).split("\n\n") if p.strip()), "")
    text = re.sub(r"[`*_#>\[\]]", "", " ".join(para.split()))
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


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
