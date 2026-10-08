"""Render tasks into a static HTML site."""

import shutil
from collections import Counter
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound

from terminal_bench_viewer.tasks import SECTIONS, Task, TaskFile

DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}

# raw html in task markdown is escaped, not rendered
md = MarkdownIt("commonmark", {"html": False}).enable("table")
fmt = HtmlFormatter(cssclass="hl", wrapcode=True)


def build_site(
    tasks: list[Task], out: Path, repo_url: str, commit: str | None = None
) -> None:
    """Write index.html, one page per task, and static assets into out."""
    env = Environment(
        loader=PackageLoader("terminal_bench_viewer"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters |= {"md": md.render, "code": render_code, "size": human_size}
    env.globals |= {"repo_url": repo_url, "commit": commit, "sections": SECTIONS}
    ref = commit or "HEAD"
    env.globals["source_url"] = lambda t, p="": f"{repo_url}/blob/{ref}/{t}/{p}"

    if out.exists():
        shutil.rmtree(out)
    (out / "tasks").mkdir(parents=True)

    tasks = sorted(tasks, key=lambda t: t.name)
    stats = {
        "difficulty": sorted(
            Counter(t.difficulty for t in tasks).items(),
            key=lambda kv: DIFFICULTY_ORDER.get(kv[0], 9),
        ),
        "category": Counter(t.category for t in tasks).most_common(),
    }
    (out / "index.html").write_text(
        env.get_template("index.html").render(tasks=tasks, stats=stats, root=".")
    )

    page = env.get_template("task.html")
    for i, t in enumerate(tasks):
        nav = {
            "prev": tasks[i - 1] if i else None,
            "next": tasks[i + 1] if i + 1 < len(tasks) else None,
        }
        (out / "tasks" / f"{t.name}.html").write_text(
            page.render(task=t, root="..", **nav)
        )

    _copy_static(out)


def render_code(f: TaskFile) -> str:
    """Syntax-highlight a text file, falling back to plain text."""
    try:
        lexer = get_lexer_for_filename(f.path, stripnl=False)
    except ClassNotFound:
        lexer = TextLexer(stripnl=False)
    return highlight(f.text or "", lexer, fmt)


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _copy_static(out: Path) -> None:
    static = out / "static"
    static.mkdir()
    for f in files("terminal_bench_viewer").joinpath("static").iterdir():
        (static / f.name).write_text(f.read_text())

    # light theme by default, dark under prefers-color-scheme
    light = HtmlFormatter(style="default").get_style_defs(".hl")
    dark = HtmlFormatter(style="github-dark").get_style_defs(".hl")
    (static / "pygments.css").write_text(
        f"{light}\n@media (prefers-color-scheme: dark) {{\n{dark}\n}}\n"
    )
