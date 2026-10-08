"""Render benchmark tasks and results into a static HTML site."""

import shutil
from collections import Counter
from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.util import ClassNotFound

from terminal_bench_viewer.benchmarks import Benchmark
from terminal_bench_viewer.results import Cell, Submission, solve_rates
from terminal_bench_viewer.tasks import SECTIONS, Task, TaskFile, strip_comments

DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}
LEVELS = 5  # heatmap color steps above zero

# raw html in task markdown is escaped, not rendered
md = MarkdownIt("commonmark", {"html": False}).enable("table")
fmt = HtmlFormatter(cssclass="hl", wrapcode=True)


@dataclass
class Edition:
    """One benchmark version with its loaded tasks and results."""

    bench: Benchmark
    tasks: list[Task]
    subs: list[Submission] = field(default_factory=list)
    commit: str | None = None  # git commit the tasks came from

    def __post_init__(self) -> None:
        self.tasks = sorted(self.tasks, key=lambda t: t.name)
        self.rates = solve_rates(self.subs)

    @property
    def difficulties(self) -> list[tuple[str, int]]:
        c = Counter(t.difficulty for t in self.tasks if t.difficulty)
        return sorted(c.items(), key=lambda kv: DIFFICULTY_ORDER.get(kv[0], 9))

    @property
    def categories(self) -> list[tuple[str, int]]:
        return Counter(t.category for t in self.tasks).most_common()

    def hardest_first(self) -> list[Task]:
        return sorted(self.tasks, key=lambda t: (self.rates.get(t.name, 2), t.name))

    def source_url(self, task: str, path: str = "") -> str | None:
        """Link to a task (or file in it) in its git repo, if it has one."""
        if not self.bench.git_url:
            return None
        return f"{self.bench.git_url}/blob/{self.commit or 'HEAD'}/{task}/{path}"


def build_site(editions: list[Edition], out: Path) -> None:
    """Write a landing page plus per-edition task, result, and static pages."""
    env = Environment(
        loader=PackageLoader("terminal_bench_viewer"),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters |= {
        # html is escaped, so comments (e.g. canary lines) would show as text
        "md": lambda s: md.render(strip_comments(s)),
        "code": render_code,
        "size": human_size,
        "level": level,
        "pct": lambda x: f"{100 * x:.0f}%",
    }
    env.globals |= {"sections": SECTIONS, "editions": editions}

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    _write(out / "index.html", env.get_template("home.html").render(root="."))

    for ed in editions:
        _build_edition(env, ed, out / ed.bench.slug)

    _copy_static(out)


def _build_edition(env: Environment, ed: Edition, out: Path) -> None:
    ctx = {"ed": ed, "root": ".."}
    _write(out / "index.html", env.get_template("index.html").render(**ctx))
    if ed.subs:
        _write(out / "results.html", env.get_template("results.html").render(**ctx))

    page = env.get_template("task.html")
    tasks = ed.tasks
    for i, t in enumerate(tasks):
        nav = {
            "prev": tasks[i - 1] if i else None,
            "next": tasks[i + 1] if i + 1 < len(tasks) else None,
        }
        html = page.render(ed=ed, task=t, root="../..", **nav)
        _write(out / "tasks" / f"{t.name}.html", html)


def level(c: Cell | None) -> int | None:
    """Heatmap color step for a cell: 0 (never passed) to LEVELS (always)."""
    if c is None or not c.n:
        return None
    # any pass at all gets at least step 1, so it never reads as zero
    return max(round(c.rate * LEVELS), 1) if c.passed else 0


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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


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
