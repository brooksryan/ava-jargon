# ava

Adversarial voice agents: mechanical voice checks and corpus-relative jargon scoring (what a mouthful). Linter-style findings, exit codes, and rate bands against human and AI baselines. Built for agents; works by hand.

## Install

Requires [uv](https://docs.astral.sh/uv/) and git.

### Quickstart with claude
```bash
uv tool install 'ava-jargon[parser] @ git+https://github.com/brooksryan/ava-jargon'
claude plugin marketplace add brooksryan/ava-jargon
claude plugin install ava-jargon@ava-jargon

claude "run ava technical check on my readme.md"
```

### Install options

With the sentence-parser tier (spacy + model, ~500 MB) (Recommended):

```bash 
uv tool install 'ava-jargon[parser] @ git+https://github.com/brooksryan/ava-jargon'
```

No parser
```bash 
uv tool install git+https://github.com/brooksryan/ava-jargon
```
### Agent Installation
See below for instructions for installing skills. 

## Usage

```bash
$ ava check draft.md --rules technical                      # findings + band summary
$ ava check - --surface chat < draft.txt                    # read stdin
$ ava jargon score draft.md -l my-lexicon.json              # jargon density + coverage
$ ava jargon build corpus/A corpus/B -o my-lexicon.json
$ ava jargon delta before/ after/ -l my-lexicon.json
$ ava jargon extend my-team slack-export.json               # profile one more approved corpus
$ ava check draft.md --rules technical --extend my-team     # its terms join the approved side
```
### Example Output
```bash
$ ava check draft.md --rules technical                      # Check markdown against technical rules
draft.md:3: [W-M1] em dash: "the deploy job — it went"
draft.md:3: [W-M2] inverted construction: "It's not a config change, it's"
draft.md:3: [W-M4] register word: "leverage"
draft.md:3: [W-M4] register word: "seamless"
checked 21 rules over 599 words: 7 findings
band summary (surface: doc-technical, 599 words):
  W-M1  1.67/1k · human 0.28-2.3 · ai ~12.5 -> PASS
  W-M2  1.67/1k · human 0.05-0.16 · ai ~0.08 -> FAIL · ai-range
  W-M4  3.34/1k · human 0.07-1.51 · ai ~0.13 -> FAIL · ai-range
$ echo $?
1
```

Findings go to stdout; everything else goes to stderr. Exit codes: 0 clean, 1 findings, 2 bad input. The verdict line names every rule the run skipped. `--json` emits one object with findings, `rules_skipped`, and per-rule band positions.

## Rules and surfaces

| `--rules` | Use on | Contents |
| --- | --- | --- |
| `westinghouse` | everything | universal rules (W-*) |
| `technical` | comments, PRs, commits, docs | + Simplified Technical English form rules (T-*) |

| `--surface` | Covers |
| --- | --- |
| `chat` | DMs, threads, channel posts, email |
| `doc-shared` | memos, guides, proposals, announcements |
| `doc-technical` | design docs, specs, runbooks (default for `--rules technical`) |
| `code` | READMEs, code comments, docstrings |

The surface picks the baseline bands and the jargon lexicon. Band verdicts are PASS, WARN, or FAIL, colored on a terminal. On `ai-high` rules, FAIL means the text matches the AI pattern. On `human-high` rules, FAIL marks a form issue and never claims AI authorship. See [CHECKS.md](CHECKS.md) for every rule, and [lexicons/README.md](lexicons/README.md) for the shipped lexicons. There is no `personal` rule set. A voice, below, holds the rules a reviewer judges for one author or one project.

## Lexicons
A lexicon represents the relative frequency of words between an APPROVED corpus and a CONTRAST corpus, where an approved corpus is "normal" and a contrast corpus has "too much jargon". This project ships with 4 prebuilt lexicons designed to identify words that AI frequently overuses, grouped by surface. 

This project allows you to extend the prebuilt lexicons so that the words you/your company/your friends use don't get flagged when you run a jargon check. 

### Extending Lexicons

No clone needed. `ava jargon extend NAME PATH...` profiles one more approved corpus into `~/.ava/extensions/NAME.json` (`AVA_HOME` moves it). `--extend NAME` on `ava check`, `ava jargon score`, or `ava jargon delta` overlays it on the lexicon in use.

```bash 
ava jargon extend my-prompts prompts.jsonl --field text --note "typed prompts, 2026"
ava check spec.md --rules technical --extend my-prompts
```

An extension adds to the approved side only. Every term the corpus uses in more than its dispersion share of documents joins the approved vocabulary, so the lexicon stops counting it as jargon. Nothing new becomes jargon. The flag repeats.

Sources: `.txt` and `.md` files count one document each. Fenced and inline code drops out of `.md` files; `--keep-code` keeps it. A `.json` or `.jsonl` file counts one document per record, and `--field` names the text field.

`--split blank` or `--split line` cuts one file into many documents. `-` reads stdin. Collect 30k+ tokens. The build prints how many terms the extension vetoes from each shipped lexicon. `ava jargon extensions` lists the profiles on this machine.

## Voices

A voice is one JSON document you own by name. It records the surface and the extensions the mechanical check runs under. It also holds a rubric a reviewer scores where mechanics cannot decide.

The rubric lists one object per rule:

1. a name
2. a description
3. criteria
4. a scoring structure: pass-fail, or a numeric scale with anchors
5. a requirement: must-pass, or a minimum score

`ava voice schema` prints the shape.

```bash
ava voice schema                                  # the JSON schema
ava voice new pm-issue voice.json                 # create ~/.ava/voices/pm-issue.json
ava voice new pm-issue voice.json --project       # create .ava/voices/pm-issue.json, committed with the repo
ava voice list                                    # every voice, project rows first
ava voice rubric pm-issue                         # the rules as a reviewer reads them; --json prints the file
echo '{"rules":[{"name":"idea-density","requirement":{"min":3}}]}' | ava voice set pm-issue
ava voice rm pm-issue
ava check issue.md --voice pm-issue               # the voice supplies --surface and --extend; a flag wins
```

A personal voice lives in `~/.ava/voices/` (`AVA_HOME` moves it). A project voice lives in `.ava/voices/` and travels with the repository; on a name clash the project voice wins. `new` and `set` refuse a document that misses the schema and name the field. `set` merges: rules merge by name, other fields replace.

The gate agents accept a voice by name. The gate runs the check under it, reads the rubric, scores every rule, and fails the verdict when a rule misses its requirement. This repository ships its own issue voice in [.ava/voices/pm-issue.json](.ava/voices/pm-issue.json). [skills/ava/references/voices.md](skills/ava/references/voices.md) walks an agent through authoring one.

## Build a lexicon

In a clone: one document per `.txt` file, 30k+ tokens per side, then

```
./ava jargon build corpus/AUDIENCE corpus/YOURS -o lexicons/mine.json
```

The approved side is the audience's vocabulary; the contrast side is the writing you test. Rules live one-per-file in `app/checks/`; after corpus or rule changes, rebuild bands with `python app/scripts/build_baselines.py`. Before you trust a rule, run it over your own writing. A rule that fires often on you is a wrong rule for you.

## Install For Your Agents

`ava setup -h` for details. `ava setup` copies the gate files into the current project and prints each path it writes by default. `-g` installs to user space, `--force` overwrites.

### Per Harness Instructions
```bash 
# Claude Code
claude plugin marketplace add brooksryan/ava-jargon
claude plugin install ava-jargon@ava-jargon

# Cursor
ava setup cursor

# Open Code
ava setup opencode

# Codex
# Codex has no subagents; the AGENTS.md block tells the agent to run `ava check` itself.
ava setup codex
ava setup agents-md >> AGENTS.md

# Gemini
gemini extensions install https://github.com/brooksryan/ava-jargon

# Everything else
ava setup skills
ava setup agents-md >> AGENTS.md
```
