---
name: ava
description: 'Voice gates for prose you produce. Run the matching gate agent to a PASS verdict before you deliver, post, or commit prose a human reads. Findings are contracts you must honor.'
---

# ava - voice gates

The `ava` CLI measures AI-authorship patterns in your prose; two gate agents enforce the rules. A gate verdict is a contract: fix every finding and re-submit until PASS. Never deliver prose that receives a FAIL verdict.

## Routing

| Prose | Gate agent | Surface |
| --- | --- | --- |
| chat message / DM / email | ava-prose-gate | `chat` |
| memo / proposal / announcement | ava-prose-gate | `doc-shared` |
| issue / ticket | ava-prose-gate | `doc-shared` |
| spec / design doc / runbook | ava-technical-gate | `doc-technical` |
| README / code comments / docstrings / PR text / commit message | ava-technical-gate | `code` |

The Claude Code plugin installs the agents as `ava-jargon:ava-prose-gate` and `ava-jargon:ava-technical-gate`.

## Invocation

Every gate requires a target (file paths or verbatim text) and a surface. `ava-technical-gate` also accepts a scope: the prose your change introduced. Pre-existing violations then report separately and never fail your change. A gate returns `INPUT_INVALID` when an input is missing: supply it and re-submit. Two rounds maximum per draft: one full review, then one confirmation pass on your fixes.

Every gate also accepts an extension: the name of an `ava jargon extend` profile for the audience. Name one when the user or the project instructions name one for that audience; `ava jargon extensions` lists the profiles on this machine.

Every gate also accepts a voice: the name of an `ava voice` profile. A voice supplies the surface and the extensions, and adds a rubric the gate scores rule by rule. Name one when the user or the project names one for that kind of document. For an extension or a voice alike: name none otherwise, and the gate never picks one itself.

`ava voice list` lists the voices on this machine. A project's shared voices live in its `.ava/voices/` directory. To create a voice, follow [references/voices.md](references/voices.md). To edit a voice, follow the same guide.

## CLI

The gates run the `ava` CLI. If a gate reports it missing:

```
uv tool install git+https://github.com/brooksryan/ava-jargon
```

## References

- Teach ava a voice: [references/voices.md](references/voices.md)
- Build a lexicon for a new audience or team: [references/custom-lexicons.md](references/custom-lexicons.md)
