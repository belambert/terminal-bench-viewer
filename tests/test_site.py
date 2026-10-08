from pathlib import Path

import pytest

from terminal_bench_viewer.benchmarks import Benchmark
from terminal_bench_viewer.results import Cell, Submission, solve_rates, tally
from terminal_bench_viewer.site import Edition, build_site, level
from terminal_bench_viewer.tasks import load_tasks

TASK_TOML = """
[task]
name = "terminal-bench/hello"
description = "Say hello."
keywords = ["basics"]
[[task.authors]]
name = "Ada"

[metadata]
difficulty = "easy"
category = "file-operations"
tags = ["io"]
expert_time_estimate_min = 5.0
junior_time_estimate_min = 10.0

[agent]
timeout_sec = 600.0

[environment]
cpus = 1
memory_mb = 2048
allow_internet = false
"""

# later versions: no difficulty or description, hours, author lists, notes
TASK_TOML_V4 = """
[task]
name = "terminal-bench/goodbye"
description = ""

[metadata]
author_name = ["Grace", "Alan"]
category = "Software"
subcategory = "Systems"
tags = []
expert_time_estimate_hours = 3
difficulty_explanation = "Needs care."
"""

GIT = Benchmark(
    "2.0", "TB 2.0", "https://example.com/r", git_url="https://example.com/r"
)
HUB = Benchmark("4.0", "TB 4.0", "https://example.com/hub", dataset="tb/tb@4.0.0")


def _task(root: Path, name: str, toml: str, instruction: str) -> Path:
    d = root / name
    for sub in ("environment", "solution", "tests"):
        (d / sub).mkdir(parents=True)
    (d / "task.toml").write_text(toml)
    (d / "instruction.md").write_text(instruction)
    (d / "environment" / "Dockerfile").write_text("FROM ubuntu:24.04\n")
    (d / "solution" / "solve.sh").write_text("echo hi > /app/out.txt\n")
    (d / "tests" / "test.sh").write_text("grep hi /app/out.txt\n")
    return d


@pytest.fixture
def bench(tmp_path: Path) -> Path:
    root = tmp_path / "bench"
    d = _task(root, "hello", TASK_TOML, "Write `hello` to <b>/app/out.txt</b>.")
    (d / "environment" / "blob.bin").write_bytes(b"\0\1\2")
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "x.pyc").write_bytes(b"\0")
    return root


@pytest.fixture
def bench_v4(tmp_path: Path) -> Path:
    root = tmp_path / "bench4"
    instr = "<!-- canary GUID abc -->\nSay **goodbye** to the server.\n\nMore detail."
    _task(root, "goodbye", TASK_TOML_V4, instr)
    _task(root, "hello", TASK_TOML_V4.replace("goodbye", "hello"), "Hi.")
    return root


def _sub(rank: int, cells: dict[str, Cell], **kw) -> Submission:
    return Submission(
        id=f"id{rank}", rank=rank, agent="Agent", model=f"Model {rank}",
        effort="high", accuracy=50.0, date=None, agent_url=None, model_url=None,
        cells=cells, **kw,
    )  # fmt: skip


def test_load_tasks(bench: Path):
    [t] = load_tasks(bench)

    assert (t.name, t.difficulty, t.category) == ("hello", "easy", "file-operations")
    assert t.tags == ["basics", "io"]
    assert t.authors == ["Ada"]
    assert [f.path for f in t.files_in("environment")] == [
        "environment/Dockerfile",
        "environment/blob.bin",
    ]
    assert t.files_in("environment")[1].text is None
    assert [f.path for f in t.files_in("other")] == ["instruction.md", "task.toml"]


def test_load_v4_metadata(bench_v4: Path):
    t = load_tasks(bench_v4)[0]

    assert t.difficulty is None and t.subcategory == "Systems"
    assert t.authors == ["Grace", "Alan"]
    assert t.expert_min == 180
    assert t.notes == {"Why it's hard": "Needs care."}
    assert t.description == ""
    assert t.summary == "Say goodbye to the server."


def test_level():
    assert level(None) is None
    assert level(Cell(5, 0)) == 0
    assert level(Cell(5, 1)) == 1
    assert level(Cell(10, 1)) == 1  # a single pass never rounds down to zero
    assert level(Cell(5, 5)) == 5


def test_tally():
    trials = [
        {"task_name": "tb/a", "rewards": {"reward": 1.0}},
        {"task_name": "tb/a", "rewards": {"reward": 0.23}},  # partial credit passes
        {"task_name": "tb/a", "rewards": {"reward": 0.0}},
        {"task_name": "tb/a", "rewards": None},  # errored
        {"task_name": "tb/b", "rewards": {"reward": 0}},
    ]
    assert tally(trials) == {"a": Cell(4, 2), "b": Cell(1, 0)}


def test_solve_rates():
    subs = [
        _sub(1, {"a": Cell(5, 5), "b": Cell(5, 0)}),
        _sub(2, {"a": Cell(5, 1), "b": Cell(5, 0)}),
    ]
    assert solve_rates(subs) == {"a": 0.6, "b": 0.0}


def test_build_site(bench: Path, tmp_path: Path):
    out = tmp_path / "site"
    build_site([Edition(GIT, load_tasks(bench), commit="abc")], out)

    assert 'href="2.0/index.html"' in (out / "index.html").read_text()
    assert 'href="tasks/hello.html"' in (out / "2.0" / "index.html").read_text()
    assert not (out / "2.0" / "results.html").exists()

    page = (out / "2.0" / "tasks" / "hello.html").read_text()
    assert "<code>hello</code>" in page
    assert "<b>" not in page  # raw html in markdown is escaped
    assert "https://example.com/r/blob/abc/hello/solution/solve.sh" in page
    assert "Binary or large file not shown" in page

    assert {p.name for p in (out / "static").iterdir()} == {
        "index.js",
        "results.js",
        "style.css",
        "pygments.css",
    }


def test_build_site_with_results(bench_v4: Path, tmp_path: Path):
    out = tmp_path / "site"
    subs = [
        _sub(1, {"goodbye": Cell(5, 0), "hello": Cell(5, 3)}),
        _sub(2, {"goodbye": Cell(5, 1)}, hacks=9.0, hacks_url="https://x/review"),
    ]
    build_site([Edition(HUB, load_tasks(bench_v4), subs)], out)

    heat = (out / "4.0" / "results.html").read_text()
    assert heat.index("goodbye.html") < heat.index("hello.html")  # hardest first
    assert 'class="c l3"' in heat and ">3/5<" in heat
    assert 'class="c na"' in heat  # submission 2 didn't run hello
    assert heat.count('href="https://x/review"') == 1
    assert "judged reward hacks (gaming the tests" in heat

    page = (out / "4.0" / "tasks" / "goodbye.html").read_text()
    assert "canary" not in page.split("<h2>Instruction</h2>")[1].split("</section>")[0]
    assert "0/5" in page and "Why it&#39;s hard" in page
    assert "GitHub" not in page  # registry datasets have no per-file links
