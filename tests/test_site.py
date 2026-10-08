from pathlib import Path

import pytest

from terminal_bench_viewer.site import build_site
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


@pytest.fixture
def bench(tmp_path: Path) -> Path:
    d = tmp_path / "bench" / "hello"
    for sub in ("environment", "solution", "tests"):
        (d / sub).mkdir(parents=True)
    (d / "task.toml").write_text(TASK_TOML)
    (d / "instruction.md").write_text("Write `hello` to <b>/app/out.txt</b>.")
    (d / "environment" / "Dockerfile").write_text("FROM ubuntu:24.04\n")
    (d / "environment" / "blob.bin").write_bytes(b"\0\1\2")
    (d / "solution" / "solve.sh").write_text("echo hello > /app/out.txt\n")
    (d / "tests" / "test.sh").write_text("grep hello /app/out.txt\n")
    (d / "__pycache__").mkdir()
    (d / "__pycache__" / "x.pyc").write_bytes(b"\0")
    return d.parent


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


def test_build_site(bench: Path, tmp_path: Path):
    out = tmp_path / "site"
    build_site(load_tasks(bench), out, repo_url="https://example.com/r", commit="abc")

    index = (out / "index.html").read_text()
    assert 'href="tasks/hello.html"' in index

    page = (out / "tasks" / "hello.html").read_text()
    assert "<code>hello</code>" in page
    assert "<b>" not in page  # raw html in markdown is escaped
    assert "https://example.com/r/blob/abc/hello/solution/solve.sh" in page
    assert "Binary or large file not shown" in page

    assert {p.name for p in (out / "static").iterdir()} == {
        "index.js",
        "style.css",
        "pygments.css",
    }
