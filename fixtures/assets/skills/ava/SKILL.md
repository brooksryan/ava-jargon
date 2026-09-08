---
name: ava
description: 'Voice gates for prose you produce. Run the matching gate agent to a PASS verdict before you deliver, post, or commit prose a human reads. Findings are contracts you must honor.'
---

# ava - voice gates

The `ava` CLI measures AI-authorship patterns in your prose; two gate agents enforce the rules. A gate verdict is a contract: fix every finding and re-submit until PASS. Never deliver prose that receives a FAIL verdict.

## Routing

| Prose | Gate agent | Voice |
| --- | --- | --- |
| chat message / DM / email | ava-prose-gate | `westinghouse` |
| memo / proposal / announcement | ava-prose-gate | `shared-docs` |
| issue / ticket | ava-prose-gate | `shared-docs` |
| spec / design doc / runbook | ava-technical-gate | `technical-docs` |
| README / code comments / docstrings / PR text / commit message | ava-technical-gate | `code` |

The Claude Code plugin installs the agents as `ava-jargon:ava-prose-gate` and `ava-jargon:ava-technical-gate`. In Codex, `ava setup codex` installs them as the custom agents `ava-prose-gate` and `ava-technical-gate`: spawn each by name.

## Invocation

When the harness lists no gate agent, install one first. In Codex, run `ava setup codex -g`. Spawn the gate next. In a harness without subagents, run `ava setup agents-md` and apply the contract it prints yourself.

Every gate requires a target (file paths or verbatim text) and a voice. `ava-technical-gate` also accepts a scope: the prose your change introduced. Pre-existing violations then report separately and never fail your change. A gate returns `INPUT_INVALID` when an input is missing: supply it and re-submit. Two rounds maximum per draft: one full review, then one confirmation pass on your fixes.

Every gate also accepts an extension: the name of an `ava jargon extend` profile for the audience. Name one when the user or the project instructions name one for that audience; `ava jargon extensions` lists the profiles on this machine.

The voice is an `ava voice` profile. The routing table names the shipped one for each kind of prose. Name a project voice instead when the user or the project names one for that kind of document. It carries the same settings, plus a rubric the gate scores rule by rule. For an extension: name none unless the user or the project names one, and the gate never picks one itself.

`ava voice list` lists the voices on this machine. A project's shared voices live in its `.ava/voices/` directory. To create a voice, follow [references/voices.md](references/voices.md). To edit a voice, follow the same guide.

## CLI

The gates run the `ava` CLI. If a gate reports it missing:

```
uv tool install git+https://github.com/brooksryan/ava-jargon
```

Without `uv`: `pip install git+https://github.com/brooksryan/ava-jargon`.

## References

- Teach ava a voice: [references/voices.md](references/voices.md)
- Build a lexicon for a new audience or team: [references/custom-lexicons.md](references/custom-lexicons.md)
