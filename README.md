# Terminal-Bench Viewer

[![pages](https://github.com/belambert/terminal-bench-viewer/actions/workflows/pages.yml/badge.svg)](https://github.com/belambert/terminal-bench-viewer/actions/workflows/pages.yml)

**Live site: https://belambert.github.io/terminal-bench-viewer/**

A static, browsable website for the
[Terminal-Bench 2.0](https://github.com/laude-institute/terminal-bench-2)
benchmark. It turns each task directory into a web page and builds a filterable
index of all tasks.

- **Index**: a searchable, sortable table of every task. You can filter it by
  difficulty and category, and the filters are kept in the URL so you can
  share a filtered view.
- **Task pages**: metadata (difficulty, category, tags, author, time
  estimates, resources, internet access), the rendered instruction and
  README, and every file in `environment/`, `solution/` and `tests/` with
  syntax highlighting. Each file links back to GitHub at the exact commit the
  site was built from.

The output is plain HTML, CSS and a small amount of JavaScript, with no
external requests. It supports light and dark mode.

## Usage

Install dependencies:

    uv sync

Build the site. This clones the benchmark into `.cache/tb2` (or pulls it if
it is already there) and writes to `site/`:

    uv run tbv build

Preview it locally:

    python -m http.server -d site

Build from an existing checkout or a fork instead:

    uv run tbv build --src ~/code/terminal-bench-2 --out /tmp/site
    uv run tbv build --repo https://github.com/you/terminal-bench-2

Binary files and text files over 200 KB are listed but not inlined. Their
pages link to GitHub instead.

## Deployment

`.github/workflows/pages.yml` builds the site and deploys it to GitHub Pages
on every push to `main`, weekly (to pick up benchmark changes), and on manual
dispatch. To enable it, set **Settings → Pages → Source** to "GitHub Actions".

## Development

    uv run pytest
    uv run black src tests && uv run isort src tests

Layout:

```
src/terminal_bench_viewer/
├── cli.py        # `tbv build` command, git clone/sync
├── tasks.py      # parse task.toml and collect task files
├── site.py       # render pages, markdown and syntax highlighting
├── templates/    # Jinja templates
└── static/       # CSS and index-page JS
```
