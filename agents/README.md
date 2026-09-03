# Agents

Two gate agents and one skill run the `ava` CLI inside an agent harness. The skill routes prose to a gate. The gate runs the mechanical check, judges the partial rules, scores a voice's rubric when the caller names one, and returns a verdict.

| File | Role |
| --- | --- |
| [ava-prose-gate.md](ava-prose-gate.md) | chat, email, memos, proposals, announcements, issues: surfaces `chat` and `doc-shared` |
| [ava-technical-gate.md](ava-technical-gate.md) | specs, runbooks, READMEs, comments, docstrings, PR text, commit messages: surfaces `doc-technical` and `code` |
| [../skills/ava/SKILL.md](../skills/ava/SKILL.md) | routing, invocation rules, the CLI install line, and references for lexicons and voices |
| [../gate-contract.md](../gate-contract.md) | the AGENTS.md block for a harness without subagents |

## Verdict

A gate returns PASS, FAIL, or INPUT_INVALID. FAIL lists every finding with an imperative fix and the judgment calls the CLI cannot make. It adds the rubric scores when a voice ran and the band rows that are WARN or FAIL. A draft gets two rounds: one full review, then one confirmation pass on the fixes. Each agent file ends with the exact verdict block.

## Install

Claude Code takes the plugin:

```bash
claude plugin marketplace add brooksryan/ava-jargon
claude plugin install ava-jargon@ava-jargon
```

Gemini takes the extension; every other harness uses `ava setup`. It copies the skill into the current project, adds the two gates where the harness has subagents, and prints each path it writes. `-g` installs to user space. `--force` overwrites.

```bash
ava setup cursor                   # .agents/skills/ava and .cursor/agents/
ava setup opencode                 # .agents/skills/ava and .opencode/agents/
ava setup codex                    # .agents/skills/ava only; then add the contract:
ava setup agents-md >> AGENTS.md   # prints gate-contract.md to stdout
gemini extensions install https://github.com/brooksryan/ava-jargon
ava setup skills                   # .agents/skills/ava only, for everything else
```

The packaged copies of these files live in `app/assets/`.
