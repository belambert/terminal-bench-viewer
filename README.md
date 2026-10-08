# Terminal-Bench Viewer

[![pages](https://github.com/belambert/terminal-bench-viewer/actions/workflows/pages.yml/badge.svg)](https://github.com/belambert/terminal-bench-viewer/actions/workflows/pages.yml)

**Live site: https://belambert.github.io/terminal-bench-viewer/**

A static, browsable website for the Terminal-Bench benchmark. It turns each
task into a web page, builds a filterable index of all tasks, and shows how
every official leaderboard submission did on every task.

It currently covers:

| Version | Tasks from                                                                         | Per-task results from                 |
|---------|------------------------------------------------------------------------------------|---------------------------------------|
| 4.0     | Harbor registry (`terminal-bench/terminal-bench@4.0.0`)                            | Harbor Hub leaderboard `4-0-0`        |
| 2.0     | [GitHub](https://github.com/laude-institute/terminal-bench-2)                      | not yet                               |

For each version the site has:

- **Task index**: a searchable, sortable table of every task, filterable by
  category (and difficulty, where tasks have one). Filters are kept in the
  URL so you can share a filtered view. When results are available it shows
  each task's solve rate across all submissions.
- **Results heatmap**: tasks × leaderboard submissions, with each cell showing
  how many trials passed. Rows can be sorted hardest-first, easiest-first, or
  by name, and hovering a cell shows the task and submission.
- **Task pages**: metadata (category, tags, author, time estimates,
  resources), the rendered instruction and README, the per-submission
  results for that task, and every file in `environment/`, `solution/` and
  `tests/` with syntax highlighting. For tasks from GitHub, files link back
  to the exact commit the site was built from.

The output is plain HTML, CSS and a small amount of JavaScript, with no
external requests. It supports light and dark mode.

## How Results Are Computed

Results come from the public Harbor Hub leaderboard. Each leaderboard row
(an agent, model, and reasoning-effort combination) lists the trials it was
scored on; the viewer reads each trial's task and reward. A cell is the
number of passing trials for that task, out of the trials run (5 for every
4.0 submission). Errored trials have no reward and count as failures, as on
the leaderboard. A task's solve rate is the mean reward across all trials of
all submissions.

These per-trial totals match the official accuracy for every 4.0 row except
Claude Code · Opus 5 (max), where they come to 52.4% against an official
51.8%; the leaderboard figure may include a manual rescore.

## Usage

Install dependencies:

    uv sync

Build the site. This downloads tasks into `.cache/` (cloning or pulling git
repos, and downloading registry datasets with `harbor download` if they
aren't cached), fetches leaderboard results, and writes to `site/`:

    uv run tbv build

Preview it locally:

    python -m http.server -d site

Build only some versions, or re-download cached registry datasets:

    uv run tbv build --only 4.0
    uv run tbv build --refresh

No Harbor login is needed; everything used is publicly readable. Binary
files and text files over 200 KB are listed but not inlined.

## Adding a Version

Versions are defined in `BENCHMARKS` in
`src/terminal_bench_viewer/benchmarks.py`. Each one names where its tasks
come from (a git repo or a Harbor registry dataset) and, optionally, the
Harbor Hub leaderboard to pull results from.

## Deployment

`.github/workflows/pages.yml` builds the site and deploys it to GitHub Pages
on every push to `main`, weekly (to pick up new tasks and submissions), and
on manual dispatch. Because the build talks to the live Harbor APIs, a
failing weekly run is also the signal that something upstream changed.

## Development

    uv run pytest
    uv run black src tests && uv run isort src tests

Layout:

```
src/terminal_bench_viewer/
├── cli.py         # `tbv build` command
├── benchmarks.py  # benchmark versions and task downloading
├── tasks.py       # parse task.toml and collect task files
├── results.py     # fetch per-task leaderboard results from Harbor Hub
├── site.py        # render pages, markdown and syntax highlighting
├── templates/     # Jinja templates
└── static/        # CSS and page JS
```
