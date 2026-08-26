# Prose gate (ava)

Run `ava check` on every piece of prose you produce before you deliver it. Prose means messages, documents, READMEs, code comments, PR text, and commit messages - not code.

1. Pick the command for the content:

| Content | Command |
| --- | --- |
| chat message / DM / email | `ava check FILE --rules westinghouse --surface chat` |
| memo / proposal / announcement | `ava check FILE --rules westinghouse --surface doc-shared` |
| spec / design doc / runbook | `ava check FILE --rules technical --surface doc-technical` |
| README / comments / docstrings / PR text / commit message | `ava check FILE --rules technical --surface code` |

2. Fix every finding. Run again until the exit code is 0.
3. Report the band summary lines that are not PASS, and any skipped rules, with your delivery.
4. Treat every finding as a contract. Do not argue with a finding. Rewrite the text.

Pass `-` as FILE to read stdin. Add `--extend NAME` when the project names an extension for its audience; `ava jargon extensions` lists them. Exit codes: 0 clean, 1 findings, 2 bad input.

If `ava` is not on PATH, run: `uv tool install git+https://github.com/brooksryan/ava-jargon`
