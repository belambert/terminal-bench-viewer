"""Command-line interface for building the site."""

import subprocess
from pathlib import Path
from typing import Annotated

import typer

from terminal_bench_viewer.site import build_site
from terminal_bench_viewer.tasks import load_tasks

REPO_URL = "https://github.com/laude-institute/terminal-bench-2"

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """Build a browsable website for Terminal-Bench."""


@app.command()
def build(
    src: Annotated[
        Path | None,
        typer.Option(help="Local benchmark checkout; cloned into --cache if omitted."),
    ] = None,
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("site"),
    cache: Annotated[Path, typer.Option(help="Clone location.")] = Path(".cache/tb2"),
    repo: Annotated[str, typer.Option(help="Benchmark git repo.")] = REPO_URL,
) -> None:
    """Generate the static site."""
    if src is None:
        src = cache
        _sync(repo, src)

    tasks = load_tasks(src)
    if not tasks:
        raise typer.BadParameter(f"no tasks (*/task.toml) found in {src}")

    build_site(tasks, out, repo_url=repo, commit=_head(src))
    typer.echo(f"built {len(tasks)} tasks -> {out}/index.html")


def _sync(repo: str, dest: Path) -> None:
    if (dest / ".git").exists():
        subprocess.run(["git", "-C", dest, "pull", "--ff-only", "-q"], check=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", repo, dest], check=True)


def _head(src: Path) -> str | None:
    r = subprocess.run(
        ["git", "-C", src, "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return r.stdout.strip() if r.returncode == 0 else None
