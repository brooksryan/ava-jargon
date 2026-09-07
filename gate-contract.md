# Prose gate (ava)

Run `ava check` on every piece of prose you produce before you deliver it. Prose means messages, documents, READMEs, code comments, PR text, and commit messages - not code.

1. Pick the command for the content:

| Content | Command |
| --- | --- |
| chat message / DM / email | `ava check FILE --voice westinghouse` |
| memo / proposal / announcement | `ava check FILE --voice shared-docs` |
| spec / design doc / runbook | `ava check FILE --voice technical-docs` |
| README / comments / docstrings / PR text / commit message | `ava check FILE --voice code` |

2. Fix every finding. Do not argue with a finding. Run again until the exit code is 0.
3. Report the band summary lines that are not PASS, and any skipped rules, with your delivery.

Pass `-` as FILE to read stdin. Add `--extend NAME` when the project names an extension for its audience; `ava jargon extensions` lists them. Use the project's own voice in place of the shipped one when the project names one for the kind of document; `ava voice list` lists them. A voice supplies the checks, the bands, the lexicon, and the extensions.

`ava voice rubric NAME` prints the rubric you judge by hand. Score each rule. Fix the draft until every rule meets its requirement.

Exit codes: 0 clean, 1 findings, 2 bad input.

If `ava` is not on PATH, run: `uv tool install git+https://github.com/brooksryan/ava-jargon`
