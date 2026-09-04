# Research

`ava` is a command-line tool that checks prose a coding agent wrote. It runs fixed-pattern rules, scores how far the vocabulary of a draft sits from its audience, and applies a rubric a reviewer scores. This directory holds the why and the evidence behind it, one document per study, and the feature docs beside the code hold the how-to. Each study defines the terms its row below uses.

I am one researcher, so each study speaks in the first person for my own work and cites outside work by source. Each study opens with a Background section that establishes the setting and the terms it uses. Each corpus appears by type and size, and no study names another person or a private corpus.

| Study | Dates | What it settled |
| --- | --- | --- |
| [Lexicon study](lexicons.md) | 2026-08-18 to 2026-08-25 | How the jargon scorer decides that a word is jargon: it compares the audience's own writing with the writing under test through five statistical tests with stated default values. Why the scorer adapts its thresholds to short and long documents, keeps one word list per kind of text, and only advises on a draft. |
| [Mechanical checks study](mechanical-checks.md) | 2026-08-21 to 2026-08-25 | Which writing rules a script can test without a reader, and which candidates fired on human writing and left. How the normal range of each rule on each kind of text came from human and AI writing samples, and which rules mark AI authorship rather than form. |

The lexicon README and the checks README link the matching study from their build and bands sections.
