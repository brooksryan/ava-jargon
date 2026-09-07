# ava

Adversarial voice agents (ava) is a cli tool that improves the readability of the docs created by your agents. The ava cli ships with 3 types of checks:

- **Mechanical Checks**: Measures stats about a document your agent wrote, compares vs human baselines. [(1)](app/checks/CHECKS.md)
- **Jargon Density**: Compares [jargon](https://developers.google.com/style/jargon) in a document vs general baseline. Extensible with your own jargon rules. [(2)](app/lexicons/README.md)
- **Personal Voice**: Customizable subjective rules. [(3)](app/voices/README.md)

Install the ava skills in your preferred harness, and tell your agent to use ava to check your docs, or use it yourself on docs your agents write. 

## Install

Requires [uv](https://docs.astral.sh/uv/) and git.

### Quickstart with claude

```bash
uv tool install 'ava-jargon[parser] @ git+https://github.com/brooksryan/ava-jargon'
claude plugin marketplace add brooksryan/ava-jargon
claude plugin install ava-jargon@ava-jargon

claude "run ava technical check on my readme.md"
```

### Quickstart with codex

```bash
uv tool install 'ava-jargon[parser] @ git+https://github.com/brooksryan/ava-jargon'
ava setup codex -g

codex "run ava technical check on my readme.md"
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

## Use

| Content | Command |
| --- | --- |
| chat message, DM, email | `ava check FILE --voice westinghouse` |
| memo, proposal, announcement, issue | `ava check FILE --voice shared-docs` |
| spec, design doc, runbook | `ava check FILE --voice technical-docs` |
| README, comments, docstrings, PR text, commit message | `ava check FILE --voice code` |

Pass `-` as FILE to read stdin. Exit codes: 0 clean, 1 findings, 2 bad input. Findings go to stdout, everything else to stderr. `--json` emits one object.

```bash
$ ava check draft.md --voice technical-docs
draft.md:3: [W-M1] em dash: "the deploy job — it went"
draft.md:3: [W-M4] register word: "leverage"
checked 21 rules over 599 words: 2 findings
band summary (bands: doc-technical, 599 words):
  W-M1  1.67/1k · human 0.28-2.3 · ai ~12.5 -> PASS
  W-M4  1.67/1k · human 0.07-1.51 · ai ~0.13 -> FAIL · ai-range
```

## Configure

`ava` writes `~/.ava/config.json` on its first run, with the version that wrote your store. Each run reads that stamp before it changes a file shape. A project config at `.ava/config.json` sets defaults for the repository and takes precedence over the personal one:

```json
{"voice": "code", "extend": [], "bands": "code"}
```

`ava config show` prints the settings a run takes and where each came from. `ava config schema` prints the shape.

## Read more

| Feature | Document |
| --- | --- |
| Rules, bands, and how to add a rule | [app/checks/README.md](app/checks/README.md); every rule in [app/checks/CHECKS.md](app/checks/CHECKS.md) |
| Lexicons: jargon scoring, extend, build | [app/lexicons/README.md](app/lexicons/README.md) |
| Voices: checks, bands, lexicon, extensions, and a rubric | [app/voices/README.md](app/voices/README.md) |
| Agents: the gates, the skill, harness setup | [agents/README.md](agents/README.md) |
| Tests: run the suite, what the image covers | [tests/README.md](tests/README.md) |
| Research: the studies behind the lexicons and the checks | [research/README.md](research/README.md) |
