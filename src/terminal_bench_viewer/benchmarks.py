"""Benchmark versions the site covers, and how to fetch their tasks."""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Benchmark:
    slug: str  # url path and cli name, e.g. "4.0"
    title: str
    source_url: str  # where people can browse the tasks
    git_url: str | None = None  # tasks from a git repo...
    dataset: str | None = None  # ...or a harbor registry dataset (org/name@version)
    leaderboard: tuple[str, str] | None = None  # hub (package, name)

    def fetch_tasks(self, cache: Path, refresh: bool = False) -> Path:
        """Download tasks into cache if needed; return the dir holding task dirs."""
        dest = cache / self.slug
        if self.git_url:
            _git_sync(self.git_url, dest)
            return dest

        assert self.dataset
        if refresh and dest.exists():
            shutil.rmtree(dest)
        if not dest.exists():
            harbor = Path(sys.executable).parent / "harbor"
            subprocess.run(
                [harbor, "download", self.dataset, "-o", dest],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        # harbor nests tasks under the dataset's org name
        return dest / self.dataset.split("/", 1)[0]


BENCHMARKS = [
    Benchmark(
        slug="4.0",
        title="Terminal-Bench 4.0",
        source_url="https://hub.harborframework.com/datasets/terminal-bench/terminal-bench",
        dataset="terminal-bench/terminal-bench@4.0.0",
        leaderboard=("terminal-bench/terminal-bench", "4-0-0"),
    ),
    Benchmark(
        slug="3.0",
        title="Terminal-Bench 3.0",
        source_url="https://hub.harborframework.com/datasets/terminal-bench/terminal-bench",
        dataset="terminal-bench/terminal-bench@3.0.0",
        leaderboard=("terminal-bench/terminal-bench", "3-0-0"),
    ),
    Benchmark(
        slug="2.0",
        title="Terminal-Bench 2.0",
        source_url="https://github.com/laude-institute/terminal-bench-2",
        git_url="https://github.com/laude-institute/terminal-bench-2",
    ),
]


def git_head(src: Path) -> str | None:
    r = subprocess.run(
        ["git", "-C", src, "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return r.stdout.strip() if r.returncode == 0 else None


def _git_sync(repo: str, dest: Path) -> None:
    if (dest / ".git").exists():
        subprocess.run(["git", "-C", dest, "pull", "--ff-only", "-q"], check=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", repo, dest], check=True)
