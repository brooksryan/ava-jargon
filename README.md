# ava - voice and jargon checks

## What this is

`ava` measures how text reads to an audience. The `check` command runs mechanical writing rules and reports findings like a linter, with a rate summary against human and AI baselines. The `jargon` commands compare two corpora and score new text against the result.

## Install

`uv` does the whole install: the venv, the dependency, and the `ava` command on your PATH.

```
uv tool install git+ssh://git@github.com/<org>/ava-jargon
ava check README.md --rules westinghouse --surface doc-shared   # smoke test
```

Update with `uv tool upgrade ava-jargon`. Remove with `uv tool uninstall ava-jargon`. To run once without an install: `uvx --from git+ssh://git@github.com/<org>/ava-jargon ava check draft.md`.

The parser tier (most T-* rules) runs automatically whenever spacy is present; without it those rules report as skipped. The optional extra adds spacy and its English model (about 500 MB):

```
uv tool install 'ava-jargon[parser] @ git+ssh://git@github.com/<org>/ava-jargon'
```

## Commands

```
./ava check draft.md --rules technical                # findings + band summary
./ava check - --surface chat < draft.txt              # pipe a chat draft in
./ava jargon score draft.md -l lexicons/NAME.json     # jargon density + coverage
./ava jargon build corpus/A corpus/B -o lexicons/NAME.json   # new lexicon
./ava jargon delta before/ after/ -l lexicons/NAME.json      # compare two sets
```

## Rule sets and surfaces

Pick the rule set for what the text IS, and the surface for where it goes:

| Set | Use on | Contents |
| --- | --- | --- |
| `westinghouse` | everything | the universal rules (W-*) |
| `technical` | comments, PRs, commits, tickets, docs | westinghouse + the STE form rules (T-*) |

| Surface | Covers | Default when |
| --- | --- | --- |
| `chat` | DMs, thread replies, channel posts, email | - |
| `doc-shared` | memos, guides, proposals, announcements | - |
| `doc-technical` | design docs, specs, runbooks, API docs | `--rules technical` |
| `code` | READMEs, code comments, docstrings | - |

The surface selects the baseline bands and the jargon lexicon. `CHECKS.md` defines every rule with examples. This build has no `personal` rule set: the personal-voice rules are custom per author and return in v3 with a build-your-own path.

## How agents read the output

1. Findings print to stdout, one per line: `path:line: [rule] label: "match"`. Everything else prints to stderr.
2. The exit code is 0 for no findings, 1 for findings, 2 for a bad input. Exit 0 alone does not prove a full measurement. The stderr verdict line - `checked 21 rules over 904 words: 0 findings (7 skipped: ...)` - names every rule the run did not test.
3. The band summary on stderr compares each rule's rate to the human band and the AI reference for the surface: `W-M1  16/1k · human 0-0.49 · ai ~7.7 -> ai-range`. Read the arrow. `ai-range` on an ai-high rule means the text reads as AI-written. A `human-high` rule is a compliance dial: humans out-score AI on it, so its summary never claims AI authorship.
4. Below 300 words the summary reports counts only. A rate from a small sample is noise.
5. W-M10 (jargon) is advisory. It prints one density line on stderr. It never joins the findings or the exit code. The matching universal lexicon loads by surface. `--lexicon` overrides.
6. Pass `--json` for one JSON object: findings, `rules_skipped`, and a `bands` object with rate, band, direction, and position per rule.

## Add your own corpus, build your own lexicon

1. Create a directory under `corpus/`, one document per `.txt` file.
2. Collect at least 30,000 tokens per side (approved and contrast, step 4). Prefer many short documents.
3. Write a `README.md` in the directory: the source and the filter rules.
4. Build: `./ava jargon build corpus/AUDIENCE corpus/YOURS -o lexicons/mine.json`. The approved side is the vocabulary of the target audience. The contrast side is the set of documents that you test for jargon.

`lexicons/README.md` lists each shipped lexicon: its two sides and its purpose.

## Tune the checks

Each rule lives in one file under `app/checks/`, and the word lists sit at the top of each file. To change a rule, edit its file. To drop a rule, delete its file and its import line in `app/checks/__init__.py`.

Validate before you trust a rule: run `ava check` over a corpus of your own messages. A rule that fires often on your own writing is a wrong rule for you. To rebuild the baselines after a corpus or rule change, run `app/scripts/build_baselines.py` with the venv python.
