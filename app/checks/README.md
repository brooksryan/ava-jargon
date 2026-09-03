# app/checks

The mechanical checkers for the v2 gate rules. `notes/mechanical-checks-plan.md` is the plan and `notes/v2-rules-proposal.html` defines each rule.

## Run the checkers

```
ava check [PATH ...] --rules westinghouse|technical|personal
          [--json] [--parser] [--lexicon PATH] [--extend NAME] [--voice NAME] [--field NAME=VALUE] [-o FILE]
```

1. `PATH` accepts a file and a directory. A directory contributes each `.md` and each `.txt` file under it. A `-` or an empty path list reads stdin, and the report then names the path `<stdin>`.
2. The report goes to stdout. A warning, a skipped-rule note, and a jargon density go to stderr, so a pipe stays clean.
3. The exit code is 0 for no findings, 1 for findings, and 2 for a bad input.
4. `--parser` adds the tier 2 rules. Without `spacy` the CLI prints a warning on stderr and runs tier 1.
5. `--lexicon` enables W-M10, and `--extend` overlays an extension on the lexicon. `--field` enables P-M5, and the flag repeats.
6. `--voice` runs the check under a named voice profile (`ava voice list`): its surface and extensions apply where the flags leave them unset. An explicit flag wins.

The default report prints one finding per line:

```
notes/plan.md:42: [W-M1] em dash: "the timer — see below"
notes/plan.md:57: [P-M1] short name: "evo-modeler" for "modeler"
```

## Add or remove a rule

Each checker holds one rule and one word list. Each checker file declares three names:

1. `RULE` holds the rule identifier, for example `"W-M1"`.
2. `SETS` holds the rule sets that include the rule.
3. `check(text, ctx)` returns the findings for one document.

`__init__.py` holds one import line per checker and one entry in `TIER_1`, `TIER_1B`, or `load_tier_2`. A new rule needs one new file and two lines. A wrong rule leaves the same way. The runner holds no discovery logic.

The runner blanks each fenced code block and each inline code span before every test. The blank holds the length of the span, so a line number stays correct.

## The rules that run

| Rule | Tier | Sets | What the checker matches |
| --- | --- | --- | --- |
| W-M1 | 1 | all | the em dash and the en dash, except an en dash in a date range |
| W-M2 | 1b | all | the "it is not X, it is Y" shape and the "not only X, but Y" shape |
| W-M3 | 1 | all | 11 assistant phrases |
| W-M4 | 1 | all | 15 register words |
| W-M6 | 1 | all | 7 hedge phrases |
| W-M7 | 1b | all | 5 throat-clearing openers, first sentence only |
| W-M8 | 1 | all | a ticket id, a process reference, a document pointer, change narration |
| W-M9 | 1 | all | an emoji cluster and an adjacent exclamation pair |
| W-M10 | 1 | all | the jargon terms of the lexicon that `--lexicon` names |
| W-M11 | 2 | all | a passive clause (`nsubjpass`, `auxpass`), promoted from W-J2 |
| T-M1 | 2 | technical | over 20 words in an instruction, over 25 in a description |
| T-M2 | 2 | technical | a second imperative verb in one sentence |
| T-M3 | 1 | technical | over 6 sentences in one prose paragraph |
| T-M4 | 2 | technical | a form of "have" and a past participle |
| T-M5 | 2 | technical | a `VBG` root verb |
| T-M7 | 2 | technical | over 3 nouns in a row inside one noun phrase |
| T-M8 | 1b | technical | 5 substitutions: commence, perform, utilize, indicate, approximately |
| T-M9 | 1b | technical | 20 known idioms |
| T-M10 | 2 | technical | "You should X" in a list item |
| T-M11 | 1 | technical | a condition word after the first clause |
| T-M12 | 1 | technical | two actions joined in one numbered item |
| P-M1 | 1 | personal | evo-modeler, evo-b-gate, evo-hydra-lib |
| P-M2 | 1 | personal | the uppercase form of 6 tech terms |
| P-M3 | 1 | personal | the agent watermark, U+2060 U+2060 and the legacy pair |
| P-M5 | 1 | personal | a missing input-contract field |

`--rules technical` and `--rules personal` both include the Westinghouse rules.

Two rules stay with the agent. The probe disqualified W-M5 superlatives, because the pattern found 32 ordinary phrases in Brooks's messages. The probe disqualified T-M6 articles, because the parse reported 10 to 13 findings on each plan that the gate already passed.

Four rules find a closed list only. W-M2, W-M7, T-M8, and T-M9 declare a `LIMIT` string that names what the agent must still judge.

## The rate on Brooks's own Slack

Work-list step 8 is the test that keeps a wrong rule out. A rule that fires often on the writing of Brooks is a wrong rule.

Command: `ava check $(ls corpus/brooks-all-slack/*.txt) --rules personal --json` Corpus: 5,733 messages that Brooks typed, 2025-12-18 to 2026-08-14. Date: 2026-08-22.

| Rule | Hits | Hits per 1,000 messages | Messages hit per 1,000 |
| --- | --- | --- | --- |
| P-M2 | 73 | 12.7 | 11.5 |
| W-M1 | 26 | 4.5 | 3.5 |
| W-M8 | 14 | 2.4 | 1.6 |
| P-M1 | 10 | 1.7 | 1.7 |
| W-M4 | 7 | 1.2 | 1.2 |
| W-M6 | 7 | 1.2 | 1.2 |
| W-M2 | 3 | 0.5 | 0.5 |
| W-M3 | 3 | 0.5 | 0.5 |
| W-M9 | 1 | 0.2 | 0.2 |
| P-M3 | 0 | 0.0 | 0.0 |

W-M10 and P-M5 need an input that this run did not supply, so both stayed out. The tier 2 rules need `--parser`, which this run did not pass.

### P-M2 was removed (2026-08-22)

P-M2 fired 12.7 times per 1,000 messages, which is 5 times the next rule. The term `qa` caused 71 of the 73 hits: Brooks writes `QA` in one message of three, so the rule contradicted his practice. Brooks also judged term casing a jargon question, not a mechanical one - the lexicon pipeline owns vocabulary. The rule is out of the checker set; `BACKLOG.md` at the project root tracks the rework. The P-M2 rows in the tables above are the record of the removed rule.

### W-M9 uses the narrow pattern

The probe tested `![^\n]{0,40}!`, which counts two separate exclamatory sentences as one cluster. That window fired 13 times, because Brooks writes "Safe travels! Welcome to Evolve!". The checker matches the adjacent pair `!!` instead, which fires once in 5,733 messages. The rule bans a cluster, and two sentences are not a cluster.

## The corpus results

| Text | Result |
| --- | --- |
| notes/speed-telemetry-plan.md and notes/cli-distribution-plan.md, `--rules technical --parser` | 0 findings |
| corpus/slack-agent-messages/before, `--rules personal` | 25 W-M1, 15 P-M1, 9 P-M2, 3 W-M8 |
| corpus/slack-agent-messages/after, `--rules personal` | 5 W-M1, 12 P-M1, 7 P-M2, 2 W-M8 |

Row 3 is the reason the checkers exist. Five dashes and twelve long names reached Slack after the voice gate passed the message.
