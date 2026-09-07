# Checks

The mechanical checkers behind `ava check`. Each rule lives in one file with its word list. [CHECKS.md](CHECKS.md) describes every rule with an example and a fix.

## Run

```
ava check [PATH ...] --voice NAME
          [--rules SET|IDS] [--bands NAME] [--lexicon PATH] [--extend NAME]
          [--json] [--no-parser] [-o FILE]
```

1. `PATH` accepts a file and a directory. A directory contributes each `.md` and each `.txt` file under it. A path of `-` or an empty path list reads stdin. The report names that path `<stdin>`.
2. Findings go to stdout, one per line. Warnings, skipped-rule notes, the jargon density, and the band summary go to stderr, so stdout carries findings only.
3. The exit code is 0 for no findings, 1 for findings, and 2 for a bad input.
4. The tier 2 rules run when spacy is present. `--no-parser` skips them. Without spacy the CLI prints a warning and runs tier 1.
5. `--voice` runs the check under a voice (`ava voice list`). Four ship: `westinghouse`, `shared-docs`, `technical-docs`, and `code`. The voice supplies the checks, the bands, the lexicon, and the extensions where the flags leave them unset. An explicit flag wins.
6. `--rules` names a rule set or rule ids such as `W-M1,W-M4`. `--bands` names a band table (`ava bands list`). `--lexicon` sets the lexicon behind W-M10, and `--extend` overlays an extension profile. The flag repeats.
7. `--json` emits one object: findings, `rules_skipped`, per-rule band positions, and the voice when one ran. `-o` writes the report to a file.

Each finding holds the file, the line, the rule, and the match:

```
notes/plan.md:42: [W-M1] em dash: "the timer — see below"
```

## Rule sets and bands

| `--rules` | Use on | Contents |
| --- | --- | --- |
| `westinghouse` | everything | the universal rules (W-M1 through W-M10) |
| `technical` | comments, PRs, commits, docs | W-* plus the Simplified Technical English form rules (T-*) |

A rule set is a shorthand for a list of rule ids. A voice names the ids it runs, and `--rules W-M1,W-M4` names them on the command line.

| `--bands` | Covers |
| --- | --- |
| `chat` | DMs, threads, channel posts, email |
| `doc-shared` | memos, guides, proposals, announcements, issues |
| `doc-technical` | design docs, specs, runbooks (the default for `--rules technical`) |
| `code` | READMEs, code comments, docstrings, PR text, commit messages |

A band table is one file under `fixtures/bands/`, and a project or personal table under `.ava/bands/` resolves by name after the shipped four. `ava bands list` names them, and `ava bands show NAME` prints one.

## Bands

The band summary compares each rule's rate per 1,000 words to a human range and an AI point from the band table. A verdict is PASS, WARN, or FAIL, colored on a terminal. Each rule has a direction:

- `ai-high` rules (W-M1 through W-M9) mark authorship signals: a FAIL in the AI range means the text matches the AI pattern.
- `human-high` rules (every T-* rule and W-M11) are form dials: a FAIL there marks a form issue and never claims AI authorship.

W-M10 jargon density is advisory. It prints as a summary line and never joins the findings or the exit code. Under 300 words the summary prints counts only, with no band comparison. [The mechanical checks study](../../research/mechanical-checks.md) gives the corpora behind the bands, the band rule, and the evidence for each direction.

## Add or remove a rule

Each checker file declares three names:

1. `RULE` holds the rule identifier, for example `"W-M1"`.
2. `SETS` holds the rule sets that include the rule.
3. `check(text, ctx)` returns the findings for one document.

`__init__.py` holds one import line per checker and one entry in `TIER_1`, `TIER_1B`, or `load_tier_2`. A new rule needs one new file and two lines. A rule leaves the same way.

The runner blanks each fenced code block and each inline code span before every test. The blank keeps the length of the span, so line numbers stay correct.

After a corpus or rule change, prepare a local JSON manifest with a `corpora` list. Each entry needs `label`, `path`, `surface`, `side`, and `origin`. Labels must be unique. Paths resolve relative to the manifest. Use `chat`, `code`, `doc-shared`, or `doc-technical` for the surface; `human` or `ai` for the side; and `universal` or `internal` for the origin. Include a human and an AI universal corpus for each surface.

An entry can name `exclude_rules`, such as `["W-M1"]` for a corpus whose format excludes dash characters. Preserve the required exclusions for each corpus format. Every configured comparison group must retain at least one corpus for each rule.

```json
{"corpora": [{"label": "public-human-chat", "path": "samples/human", "surface": "chat", "side": "human", "origin": "universal", "exclude_rules": []}]}
```

The example shows one entry. Add the remaining corpora before you run the command. Keep private corpus manifests outside version control.

```bash
python app/scripts/build_baselines.py --manifest /path/to/inputs.json --output tmp/calibration/review-1
```

The rebuild requires the parser extra and all 22 calibration checks. It stops if a required input or check is unavailable. The output directory must be new and outside `fixtures/` and `app/`. It contains `baselines_run.json` and four tables under `bands/`. The run records the analysis time, input hashes, document and word counts, and completed checks. Review the tables before copying them to `fixtures/bands/`.

For a complete cached run, add `--reuse tmp/calibration/review-1/baselines_run.json`. Choose a new output directory. The sources, manifest, and analysis code must match the cached run. Before you trust a rule, run it over a sample of the audience's own writing. A rule that fires often there is a wrong rule for that audience.

## The rules that run

| Rule | Tier | Sets | What the checker matches |
| --- | --- | --- | --- |
| W-M1 | 1 | all | the em dash and the en dash, except an en dash in a date range |
| W-M2 | 1b | all | the `it is not X, it is Y` shape and the `not only X, but Y` shape |
| W-M3 | 1 | all | 11 assistant phrases |
| W-M4 | 1 | all | 15 register words |
| W-M6 | 1 | all | 7 hedge phrases |
| W-M7 | 1b | all | 5 fixed openers, first sentence only |
| W-M8 | 1 | all | a ticket id, a process reference, a document pointer, change narration |
| W-M9 | 1 | all | an emoji cluster and an adjacent exclamation pair |
| W-M10 | 1 | all | the jargon terms of the lexicon that `--lexicon` names |
| W-M11 | 2 | technical | a passive clause (`nsubjpass`, `auxpass`) |
| T-M1 | 2 | technical | over 20 words in an instruction, over 25 in a description |
| T-M2 | 2 | technical | a second imperative verb in one sentence |
| T-M3 | 1 | technical | over 6 sentences in one prose paragraph |
| T-M4 | 2 | technical | a form of "have" and a past participle |
| T-M5 | 2 | technical | a `VBG` root verb |
| T-M7 | 2 | technical | over 3 nouns in a row inside one noun phrase |
| T-M8 | 1b | technical | 5 substitutions: `commence`, `perform`, `utilize`, `indicate`, `approximately` |
| T-M9 | 1b | technical | 20 known idioms |
| T-M10 | 2 | technical | "You should X" in a list item |
| T-M11 | 1 | technical | a condition word after the first clause |
| T-M12 | 1 | technical | two actions joined in one numbered item |

Four rules find a closed list only. W-M2, W-M7, T-M8, and T-M9 declare a `LIMIT` string that names what the gate agent must still judge.
