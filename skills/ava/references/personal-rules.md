# Personal voice rules

This build ships no `--rules personal`. The personal rules (P-*) - short-name preferences, term casing, watermark detection, the message input contract - are custom per author. A rule calibrated on one author's writing misfires on another's. A fixed list would fail the same test the shipped rules must pass. Version 3 adds a build-your-own path; until then, this page describes what you can do today.

## The validity test

Every rule and term list must pass one test before you enforce it: run it over a corpus of the author's own writing. A rule that fires often on the author is a wrong rule for that author. Example from this project's history: a lowercase-term rule flagged `qa` at 12.7 per 1,000 words on the author's own messages. The author writes `QA` in one message of three. We dropped the rule and kept the habit.

## What you can build today

1. **A personal lexicon.** Collect the author's own messages as the approved side. Collect agent drafts as the contrast side. Build a lexicon from the two - see [custom-lexicons.md](custom-lexicons.md). Score drafts with it. High density marks vocabulary the author never uses.
2. **A personal judgment anchor.** When a gate must judge whether text sounds like the author, give it a sample of the author's recent writing from the same surface. Have the gate cite the samples in its findings. Judgment anchored on real samples beats a rule list nobody calibrated.

## What returns in v3

Per-author P-* rules arrive with a calibration step. Each candidate rule first runs over the author's corpus and reports its fire rate. It enters the ruleset only when the author accepts it.
