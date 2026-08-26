# ava - voice and jargon checks

## What this is

`ava` measures the style signals in text. The `check` command runs mechanical writing rules and reports findings like a linter, with a band summary against human and AI baselines. The `jargon` commands compare two corpora and score new text against the result. Coding agents are the intended callers, and every command also works by hand.

## Install

`uv` does the whole installation: the venv, the `wordfreq` dependency, and the `ava` command on your PATH.

```
uv tool install git+https://github.com/brooksryan/ava-jargon
ava check README.md --rules westinghouse --surface doc-shared   # smoke test
```

Update with `uv tool upgrade ava-jargon`. Remove with `uv tool uninstall ava-jargon`. To run `ava` once without an installation, use: `uvx --from git+https://github.com/brooksryan/ava-jargon ava check draft.md`.

Some rules need a sentence parser: the T-* rules in the table below. When spacy is present, the parser tier runs automatically. Without spacy, the run reports the T-* rules as skipped. The optional extra adds spacy and its English model (about 500 MB):

```
uv tool install 'ava-jargon[parser] @ git+https://github.com/brooksryan/ava-jargon'
```

## Commands

```
ava check draft.md --rules technical                 # findings + band summary
ava check - --surface chat < draft.txt               # pipe a chat draft in
ava jargon score draft.md -l my-lexicon.json         # jargon density + coverage
ava jargon build corpus/A corpus/B -o my-lexicon.json    # new lexicon
ava jargon delta before/ after/ -l my-lexicon.json       # compare two sets
```

In a clone of this repository, prefix each command with `./` instead.

## Rule sets and surfaces

Pick the rule set for the type of the text. Pick the surface for the destination of the text.

| Set | Use on | Contents |
| --- | --- | --- |
| `westinghouse` | everything | the universal rules (W-*) |
| `technical` | comments, PRs, commits, tickets, docs | westinghouse + the Simplified Technical English (STE) form rules (T-*) |

| Surface | Covers | Default when |
| --- | --- | --- |
| `chat` | DMs, thread replies, channel posts, email | - |
| `doc-shared` | memos, guides, proposals, announcements | - |
| `doc-technical` | design docs, specs, runbooks, API docs | `--rules technical` |
| `code` | READMEs, code comments, docstrings | - |

The surface selects the baseline bands and the jargon lexicon. `CHECKS.md` defines every rule with examples. This version has no `personal` rule set. The personal rules are custom for each author. A later version will let you build your own.

## How to read the output

1. The command prints findings to stdout, one per line: `path:line: [rule] label: "match"`. It prints all other output to stderr.
2. The exit code is 0 for no findings, 1 for findings, and 2 for a bad input. Exit 0 alone does not prove a full measurement. The stderr verdict line - `checked 21 rules over 904 words: 0 findings (7 skipped: ...)` - names every rule the run did not test.
3. The band summary on stderr compares each rule's rate to the human band and the AI reference for the surface. Example: `W-M1  16/1k · human 0-0.49 · ai ~7.7 -> ai-range`. Read the arrow. On an ai-high rule, where AI text scores higher than human text, `ai-range` means the text matches the AI pattern. A `human-high` rule measures compliance. Humans score higher than AI on it, so its summary never claims AI authorship.
4. Below 300 words the summary reports counts only. A rate from a small sample is noise.
5. W-M10 (jargon) is advisory. It prints one density line on stderr. It never appears in the findings. It never changes the exit code. `ava` loads the universal lexicon that matches the surface. The `--lexicon` option overrides the default lexicon.
6. Pass `--json` for one JSON object: findings, `rules_skipped`, and a `bands` object with rate, band, direction, and position per rule.

## Add your own corpus, build your own lexicon

These steps run in a clone of this repository.

1. Create a directory under `corpus/`. Put one document in each `.txt` file.
2. Collect at least 30,000 tokens per side (approved and contrast, step 4). Prefer many short documents.
3. Write a `README.md` in the directory. Record the source and the filter rules in it.
4. Build: `./ava jargon build corpus/AUDIENCE corpus/YOURS -o lexicons/mine.json`. The approved side is the vocabulary of the target audience. The contrast side is the set of documents that you test for jargon.

`lexicons/README.md` lists each shipped lexicon: its two sides and its purpose.

## Tune the checks

These steps also run in a clone. Each rule is in one file under `app/checks/`. The word lists are at the top of each file. To change a rule, edit its file. To delete a rule, delete its file and its import line in `app/checks/__init__.py`.

Before you trust a rule, run `ava check` over a corpus of your own messages. A rule that fires often on your own writing is a wrong rule for you. After a corpus or rule change, rebuild the baselines with `python app/scripts/build_baselines.py` (this needs the parser extra).
