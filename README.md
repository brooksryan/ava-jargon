# ava

Adversarial voice agents: mechanical voice checks and corpus-relative jargon scoring. Linter-style findings, exit codes, and rate bands against human and AI baselines. Agents run it in a harness, and a person can run it from a shell.

## Install

Requires [uv](https://docs.astral.sh/uv/) and git. The parser tier adds spacy and a model, about 500 MB, and runs the sentence-level rules.

```bash
uv tool install 'ava-jargon[parser] @ git+https://github.com/brooksryan/ava-jargon'   # with the parser tier
uv tool install git+https://github.com/brooksryan/ava-jargon                          # without it
```

For Claude Code, add the plugin. It installs two gate agents and the `ava` skill:

```bash
claude plugin marketplace add brooksryan/ava-jargon
claude plugin install ava-jargon@ava-jargon
claude "run ava technical check on my README.md"
```

## Use

| Content | Command |
| --- | --- |
| chat message, DM, email | `ava check FILE --rules westinghouse --surface chat` |
| memo, proposal, announcement, issue | `ava check FILE --rules westinghouse --surface doc-shared` |
| spec, design doc, runbook | `ava check FILE --rules technical --surface doc-technical` |
| README, comments, docstrings, PR text, commit message | `ava check FILE --rules technical --surface code` |

Pass `-` as FILE to read stdin. Exit codes: 0 clean, 1 findings, 2 bad input. Findings go to stdout, everything else to stderr. `--json` emits one object.

```bash
$ ava check draft.md --rules technical
draft.md:3: [W-M1] em dash: "the deploy job — it went"
draft.md:3: [W-M4] register word: "leverage"
checked 21 rules over 599 words: 2 findings
band summary (surface: doc-technical, 599 words):
  W-M1  1.67/1k · human 0.28-2.3 · ai ~12.5 -> PASS
  W-M4  1.67/1k · human 0.07-1.51 · ai ~0.13 -> FAIL · ai-range
```

## Read more

| Feature | Document |
| --- | --- |
| Rules, surfaces, bands, and how to add a rule | [app/checks/README.md](app/checks/README.md); every rule in [app/checks/CHECKS.md](app/checks/CHECKS.md) |
| Lexicons: jargon scoring, extend, build | [app/lexicons/README.md](app/lexicons/README.md) |
| Voices: a named surface, extensions, and rubric | [app/voices/README.md](app/voices/README.md) |
| Agents: the gates, the skill, harness setup | [agents/README.md](agents/README.md) |
