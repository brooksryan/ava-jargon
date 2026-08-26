---
name: ava description: 'Voice gates for prose you produce. Run the matching gate agent first. Do this before you deliver, post, or commit prose a human reads. You need a PASS verdict before you deliver. Findings are contracts you must honor.'
---

# ava - voice gates

Your default prose reads like an AI wrote it. The user decided which patterns are unacceptable. The `ava` CLI measures them; two gate agents enforce them. A gate verdict is a contract: fix every finding and re-submit until PASS. Never deliver on FAIL.

## Routing

| Prose | Gate agent | Surface |
| --- | --- | --- |
| chat message / DM / email | ava-prose-gate | `chat` |
| memo / proposal / announcement | ava-prose-gate | `doc-shared` |
| spec / design doc / runbook | ava-technical-gate | `doc-technical` |
| README / code comments / docstrings / PR text / commit message | ava-technical-gate | `code` |

The Claude Code plugin installs the agents as `ava-jargon:ava-prose-gate` and `ava-jargon:ava-technical-gate`.

## Invocation

Every gate requires a target (file paths or verbatim text) and a surface. `ava-technical-gate` also accepts a scope: the prose your change introduced. Pre-existing violations then report separately and never fail your change. A gate returns `INPUT_INVALID` when an input is missing: supply it and re-submit. Two rounds maximum per draft: one full review, then one confirmation pass on your fixes.

## CLI

The gates run the `ava` CLI. If a gate reports it missing:

```
uv tool install git+https://github.com/brooksryan/ava-jargon
```

## References

- Build a lexicon for a new audience or team: [references/custom-lexicons.md](references/custom-lexicons.md)
- Personal voice rules and per-author calibration: [references/personal-rules.md](references/personal-rules.md)
