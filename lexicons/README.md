# Lexicons

One row per shipped lexicon. `ava check` picks the universal lexicon that matches the band surface when the caller passes no `--lexicon`.

| File | Approved side (the audience) | Contrast side (scored against) | Surface |
| --- | --- | --- | --- |
| universal-chat.json | HN, Ubuntu IRC, W3C mail, Enron (pre-2022) | generated Claude chat + 2024 GPT-4 turns | chat |
| universal-doc-shared.json | Berkshire, Bezos, PG, Marks, Grantland, Increment, plain-language, Wikipedia (pre-2022) | AI blogposts + AI marketing (post-2024) | doc-shared |
| universal-doc-technical.json | RFCs, PostgreSQL/Django/Rust docs, arXiv, distill.pub, SRE book (pre-2022) | agent-trailer GitHub docs (post-2024) | doc-technical |
| universal-code.json | GitHub READMEs + comments (pre-2022) | agent-trailer READMEs + comments (post-2024) | code |


> **NOTE:** The AI corpora write about AI, so terms like `claude`, `ai`, and `seo` top these lists. The density signal separates the sides; a single term hit does not. W-M10 stays advisory for exactly this reason.


`ava jargon extend` adds one more approved corpus to any of these at check time; see the README. The `analysis-*` files are Brooks's local research lexicons and do not ship. Rebuild any universal lexicon with the `ava jargon build` commands recorded in the project notes.
