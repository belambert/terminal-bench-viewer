"""Command-line interface for building the site."""

from pathlib import Path
from typing import Annotated

import typer

from terminal_bench_viewer.benchmarks import BENCHMARKS, git_head
from terminal_bench_viewer.results import fetch_leaderboard
from terminal_bench_viewer.site import Edition, build_site
from terminal_bench_viewer.tasks import load_tasks

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """Build a browsable website for Terminal-Bench."""


@app.command()
def build(
    out: Annotated[Path, typer.Option(help="Output directory.")] = Path("site"),
    cache: Annotated[Path, typer.Option(help="Task download dir.")] = Path(".cache"),
    only: Annotated[
        list[str] | None,
        typer.Option(help="Benchmark version(s) to build, e.g. 4.0. Default: all."),
    ] = None,
    refresh: Annotated[
        bool, typer.Option(help="Re-download registry datasets.")
    ] = False,
) -> None:
    """Fetch tasks and results, then generate the static site."""
    benches = [b for b in BENCHMARKS if not only or b.slug in only]
    if not benches:
        raise typer.BadParameter(f"unknown version(s): {only}")

    editions = []
    for b in benches:
        src = b.fetch_tasks(cache, refresh)
        tasks = load_tasks(src)
        if not tasks:
            raise typer.BadParameter(f"no tasks (*/task.toml) found in {src}")
        subs = fetch_leaderboard(*b.leaderboard) if b.leaderboard else []
        commit = git_head(src) if b.git_url else None
        editions.append(Edition(b, tasks, subs, commit))
        typer.echo(f"{b.title}: {len(tasks)} tasks, {len(subs)} submissions")

    build_site(editions, out)
    typer.echo(f"built -> {out}/index.html")
