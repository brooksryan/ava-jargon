# Release tools

`app/scripts/` holds the tools that prepare or maintain a release. Each tool runs from the repository root with the development interpreter. Only the source archive ships this directory.

| Tool | Maintains | Run |
| --- | --- | --- |
| `build_baselines.py` | the band tables under `fixtures/bands/` | `python app/scripts/build_baselines.py --manifest /path/to/inputs.json` |
| `build_research_figures.py` | the figures under `research/figures/` | `python app/scripts/build_research_figures.py [DIR]` |
| `unwrap_md.py` | one line per paragraph in each committed `.md` file | `git config core.hooksPath githooks` |

## Calibration

`build_baselines.py` computes the band tables from a corpus manifest. It needs the `parser` extra. [The checks README](../checks/README.md) describes the manifest, the review directory, and the `--reuse` flag. A release takes the reviewed tables from a complete run. The tool reads only the corpus paths that the manifest names.

## Figures

`build_research_figures.py` draws each figure of the research studies from the numbers in the script and writes one SVG file per figure to `research/figures/`. Pass a directory to write elsewhere. The test suite regenerates the figures and compares them with the shipped files. A change to a number in a study needs the same change in the script.

## Markdown hook

`githooks/pre-commit` runs `unwrap_md.py` over each staged `.md` file and stages the result. The script joins a wrapped continuation line to the line above it. Code fences, headings, tables, list markers, quotes, and front matter keep their own lines. Run `git config core.hooksPath githooks` once per clone.

## Research scripts

Corpus collectors, corpus mining, and one-off reports do not live in this repository. Keep them in a local directory outside the checkout, together with the corpora and audit data they read. The test suite fails when this directory holds a file outside the table above, or when a tool names `corpus/`, `audit/`, or `notes/`.
