# Mechanical checks study

`ava` is a command-line tool that checks prose a coding agent wrote. `ava check` runs a set of checkers, each one a fixed string or shape a script tests without a reader. This study records how I chose those checkers, dropped the candidates that failed, and derived the bands the summary compares a draft against. I ran the study from 2026-08-21 to 2026-08-25.

## Background

I work at a software company and run coding agents: language-model assistants that write code, documents, and chat messages from my terminal. Between June and August 2026 I ran eight review agents beside them. A review agent is a prompt file with a rule list and a verdict format. A coding agent drafts a chat message, a code comment, or a document. A review agent then reads the draft against its rules and returns PASS or FAIL with findings. I call such an agent a judgement gate, because a language model reads and judges every rule.

Four of the eight covered chat in my own voice, code comments, process language in prose, and the form rules of Simplified Technical English. One judged general voice, and three judged application text. Their prompt files held 130 rule lines between them.

The study uses these terms throughout:

1. A rule is one numbered entry from a rule list, for example W-M1. A mechanical rule matches a fixed string or shape. A judgement rule needs a reader.
2. A checker is the script that tests one mechanical rule. A finding is one hit: the rule, the line, and the matched text.
3. A tier groups checkers by dependency. Tier 1 needs the standard library. Tier 1b finds a closed list and leaves the rest to the gate. Tier 2 needs the `spacy` parser.
4. A surface is the kind of text under check: `chat`, `doc-shared`, `doc-technical`, or `code`.
5. A corpus is a directory of documents, one text file each. My corpus library holds human corpora and AI corpora for each surface.
6. A band is the range of a rule's rate, in findings per 1,000 words, across the human corpora of one surface. The AI reference is the median rate across the AI corpora of that surface.
7. Simplified Technical English is ASD-STE100, an aerospace writing standard with rules on sentence length, tense, and one word per meaning. The T-* rules come from it. The appendix cites it.
8. The universal rule set is `westinghouse` in the CLI. The `technical` set adds the T-* rules and W-M11.
9. A hard negative is an AI corpus with proof of authorship. A soft negative is a corpus with likely AI influence and no proof. A control is a corpus that lacks the signal under test.
10. A percentile rank places one rate among all 37 corpus-level rates for a rule, low to high. A rate at the 90th percentile sits above 90 percent of the corpora.

Each rule id below names one check. [The check catalog](../app/checks/CHECKS.md) states the trigger, an example, and a fix for every shipped universal and technical rule. The personal layer ships outside the catalog. The rules this study leans on:

| Rule | Trigger |
| --- | --- |
| W-M1 dash | an em dash or an en dash |
| W-M2 inverted construction | the shape `it is not X, it is Y` |
| W-M3 assistant phrases, W-M4 register words, W-M6 hedge phrases | a word or phrase from a fixed list |
| W-M5 superlatives | "the best way", "the cleanest approach"; a candidate that never shipped |
| W-M7 opener | a fixed throat-clearing first sentence |
| W-M8 process language | a ticket id, a sprint or phase reference, or change narration |
| W-M9 clusters | adjacent emoji or the pair `!!` |
| W-M11 passive voice | a passive clause |
| T-M1 sentence length, T-M4 perfect tenses, T-M5 -ing main verb, T-M7 noun clusters | the Simplified Technical English form rule of that name |
| T-M6 articles required | a dropped article; a candidate that never shipped |
| P-M1 short names, P-M2 lowercase terms, P-M3 watermark | my long repository names, the uppercase form of a technical term, the chat watermark |

Two facts about my own chat corpus matter below. Agent-posted messages in my team's chat carry an invisible character pair, a watermark, so I can separate them from messages I typed. My team's repositories have long formal names and the short names I type. The agents typed the long ones, and the short-name rule P-M1 counts each long name.

## Question

Which voice rules can a script test, and does each one separate human writing from AI writing on each surface? I asked three things. What does a checker catch that a judgement gate misses? Which candidate rules fire on human writing? What rate counts as normal for each rule on each surface?

## Method

I ran the study in five steps.

### Rule consolidation

The eight review agents held 130 rule entries: 59 mechanical and 71 judgement. I removed 47 duplicates. The dash ban appeared in five agents, and the inverted-construction ban in seven of eight. The 54 rules that remained fell into three layers.

| Layer | Prefix | Mechanical | Judgment | Source |
| --- | --- | --- | --- | --- |
| universal | W | 10 | 12 | the rules every agent shared |
| technical form | T | 12 | 6 | ASD-STE100 |
| personal | P | 5 | 9 | my own register |

Only the mechanical rules were candidates for a checker.

### The feasibility probe

I ran each candidate checker over four text sets. The probe sorted the candidates into the three tiers.

### The own-writing test

I ran every checker over 5,733 chat messages I typed. A rule that fires often on the writing of the audience is a wrong rule for that audience. This step decides whether a rule stays.

### The check matrix

I ran every checker over 17 corpora: 22 checkers, 8,634 documents, about 840k words. The script is `app/scripts/check_matrix.py`. The matrix reports findings per 1,000 words for each rule on each corpus.

### The baseline bands

I ran every checker over 37 corpora mapped to four surfaces, a human or AI side, and a public or internal origin. The script is `app/scripts/build_baselines.py`, and the output is `app/checks/baselines.json`. The human band is the minimum and the maximum corpus-level rate across the human corpora of the surface. The AI reference is the median across the AI corpora. Public and internal bands compute separately. A sample under 300 words gets counts only, because one dash in 200 words reads as 5 per 1,000.

## Data

The probe used four text sets.

| Text set | Documents | Words |
| --- | --- | --- |
| plans that passed two judgement gates | 2 | about 4k |
| agent chat drafts that failed a judgement gate | 16 | 1.7k |
| the same drafts as posted after the gate | 16 | 1.4k |
| my messages, eight months | 5,733 | 87k |

The bands rest on 37 corpora. The human side is human by era, published before 2022, or by the watermark. A sweep also moved 42 hand-pasted agent messages from the human chat corpora to the AI side. Each corpus on the AI side has proof of authorship. The proof is a dataset label, a named generating model, a coding-agent commit trailer, or admission by the mechanical checks.

### Chat

| Side | Origin | Corpus type | Documents | Words |
| --- | --- | --- | --- | --- |
| human | public | technology-forum comments, pre-2022 | 1,400 | 132k |
| human | public | IRC support chat, pre-2022 | 103 | 111k |
| human | public | standards mailing-list email, pre-2022 | 624 | 101k |
| human | public | workplace email, 2001 era | 1,051 | 118k |
| human | internal | my messages | 5,711 | 86k |
| human | internal | my team's messages | 1,282 | 53k |
| human | internal | end-user messages | 346 | 14k |
| human | internal | end-user ticket comments | 146 | 8k |
| human | internal | my typed prompts to a coding agent | 1,354 | 53k |
| AI | public | generated assistant replies, three model tiers | 120 each | 28k, 24k, 25k |
| AI | public | 2024 frontier-model turns | 258 | 84k |
| AI | internal | agent drafts before a judgement gate | 16 | 1.7k |
| AI | internal | agent text pasted into messages by hand | 42 | 4k |

### Document, shared

| Side | Origin | Corpus type | Documents | Words |
| --- | --- | --- | --- | --- |
| human | public | shareholder letters, two companies | 31 and 23 | 371k and 48k |
| human | public | startup essays, pre-2022 | 149 | 345k |
| human | public | investor memos | 72 | 332k |
| human | public | longform journalism | 60 | 209k |
| human | public | software-magazine articles | 161 | 339k |
| human | public | plain-language government guides | 316 | 208k |
| human | public | encyclopedia computing articles | 228 | 39k |
| AI | public | blog posts, post-2024 | 44 | 75k |
| AI | public | marketing copy, post-2024 | 68 | 166k |

### Document, technical

| Side | Origin | Corpus type | Documents | Words |
| --- | --- | --- | --- | --- |
| human | public | standards documents | 56 | 292k |
| human | public | open-source project documentation, pre-2022 | 124 | 299k |
| human | public | computer-science preprints, pre-2022 | 313 | 240k |
| human | public | technical exposition articles | 50 | 183k |
| human | public | a reliability-engineering book | 61 | 285k |
| AI | public | agent-authored repository documents, post-2024 | 314 | 529k |
| AI | internal | planning documents my agents wrote | 249 | 422k |
| AI | internal | how-to guides my agents wrote | 39 | 36k |

### Code

| Side | Origin | Corpus type | Documents | Words |
| --- | --- | --- | --- | --- |
| human | public | READMEs, pre-2022 | 80 | 170k |
| human | public | code comments, pre-2022 | 1,429 | 69k |
| AI | public | agent-authored READMEs, post-2024 | 70 | 68k |
| AI | public | agent-authored code comments, post-2024 | 1,217 | 48k |

Two groups stayed out of the bands. Output of pre-2024 chat models lacks the dash signal and serves as a control. Post-2024 preprints carry the names of human authors and possible model polish, so they serve as a soft negative only.

## Results

### Probe results

| Text set | Findings |
| --- | --- |
| plans that passed two judgement gates | 0 |
| agent drafts that failed a judgement gate | 25 dash, 15 short-name |
| the same drafts as posted | 5 dash, 12 short-name |
| my messages | 27 dash, or 4.7 per 1,000 messages |

The third row is the reason the checkers exist. Five dashes and twelve long repository names reached the chat channel after a judgement gate passed the message. A regular expression finds every one of them. The fourth row tests the rule against the audience. I type a dash in 0.5 percent of my messages, so the dash ban matches my own practice.

### The own-writing rates

The table gives hits per 1,000 messages over my 5,733 messages.

| Rule | Hits per 1,000 messages |
| --- | --- |
| P-M2 lowercase terms, dropped | 12.7 |
| W-M1 dash | 4.5 |
| W-M8 process language | 2.4 |
| P-M1 short names | 1.7 |
| W-M4 register words | 1.2 |
| W-M6 hedge phrases | 1.2 |
| W-M2 inverted construction | 0.5 |
| W-M3 assistant phrases | 0.5 |
| W-M9 clusters | 0.2 |
| P-M3 watermark | 0.0 |

### Matrix results

1. W-M1 dash is the cleanest separator. My messages run 0.30 per 1,000 words and the workplace email runs 0. Every agent corpus runs 11.5 to 14.3. A judgement gate cut the drafts from 14.3 to 3.65 and did not reach zero.
2. P-M1 short names survives a judgement gate untouched: 8.61 before and 8.77 after, against 0.11 on my messages.
3. W-M8 process language fell from 12.4 to 0 on code comments after a comment gate. Agent documents still carry 2.69.
4. T-M1, T-M4, and T-M5 fire on every human conversation corpus. My messages run 8.72 on T-M5, and the encyclopedia articles run 14.3 on T-M1. These are form rules for documents, and the personal layer suspends them.
5. W-M11 passive voice runs 5.28 on my messages and 5 to 12 on every human corpus. Passive is normal register in conversation.
6. W-M7 opener returned zero across all 17 corpora.
7. W-M2, W-M3, W-M6, and W-M9 sit near zero everywhere, agent drafts included. Their value is to block a single incident, and their base rate is too low to band.

### Band results

The W-M1 dash gap holds on every surface. The table gives the public human band and the public AI reference in findings per 1,000 words.

| Surface | Human band | AI reference |
| --- | --- | --- |
| chat | 0 to 0.49 | 7.68 |
| doc-shared | 1.11 to 6.37 | 8.29 |
| doc-technical | 0.28 to 2.30 | 12.52 |
| code | 0 to 0.12 | 9.43 |

The doc-shared band is the widest, because the letter and essay writers use dashes. The internal chat AI reference sits at 14.04 against a human band of 0 to 0.45. The percentile rank of each side's median rate tells the same story. Across the four surfaces the human median sits between the 9th and the 61st percentile. The AI median sits between the 77th and the 93rd.

Three more universal rules separate the sides on some surfaces. W-M4 register words: doc-shared humans run 0.10 to 1.05 against an AI reference of 1.61. W-M8 process language: doc-technical humans run 0 to 0.08 against 1.42. W-M2 inverted construction: doc-shared humans run 0.08 to 0.48 against 0.50, a marginal gap.

The T-* rules and W-M11 read backwards on every surface. Humans out-score AI on sentence length, perfect tenses, and passive voice. On doc-technical, humans run 11.6 to 14.2 on T-M1 against an AI reference of 7.01, and 7.9 to 19.5 on W-M11 against 7.27. These rules measure form compliance and never authorship.

### Rules that failed or changed

| Rule | Evidence | Outcome |
| --- | --- | --- |
| W-M5 superlatives | 32 hits on my messages, most of them ordinary speech such as "the best way to go" | stays a judgement rule |
| T-M6 articles required | 10 to 13 findings on each plan that two gates passed; mass nouns and prepositional phrases defeat the test | stays a judgement rule |
| P-M2 lowercase terms | 12.7 hits per 1,000 messages, five times the next rule; one term caused 71 of 73 hits, and I write its uppercase form in one message of three | dropped; term casing belongs to the lexicon |
| W-M9 clusters | the window `![^\n]{0,40}!` fired 13 times on two exclamatory sentences | narrowed to the adjacent pair `!!`, one hit in 5,733 messages |
| W-M11 passive voice | 5 to 12 per 1,000 words on every human chat corpus | moved from the universal set to the technical set |
| W-M2 inverted construction | 7 of 8 review agents carried it, and a checker finds only the fixed shape | tier 1b: the checker finds the shape, the gate judges the contrast pair |
| T-M7 noun clusters | the sentence splitter joined heading lines into one six-noun run | the parser tier blanks headings, tables, and list markers first |
| W-M1 dash | one standards corpus is ASCII-only, and my typed prompts quote pasted agent output | both corpora excluded from the W-M1 band as format artifacts |
| W-M7 opener | zero across all 17 corpora | kept as a tier 1b backstop; the gate judges the first sentence |

## Decisions

1. Three tiers by dependency. Tier 1 and 1b need the standard library. Tier 2 needs `spacy`, ships as the `[parser]` extra, and `--no-parser` skips it.
2. One file per checker under `app/checks/`. Each file declares `RULE`, `SETS`, and `check`. A tier 1b file also declares `LIMIT`, the part the gate must still judge.
3. Two rule sets. `westinghouse` holds W-M1 through W-M4 and W-M6 through W-M10 for every surface, and W-M5 stays a judgement rule. `technical` adds the T-* rules and W-M11 for documents and prose beside code.
4. Bands per rule per surface. The matrix showed 5x to 10x rate differences between surfaces for one rule, so one band per rule was wrong. The surfaces are `chat`, `doc-shared`, `doc-technical`, and `code`.
5. The human band is the minimum and maximum corpus-level rate, and the AI reference is the median. Public and internal bands ship side by side in `app/checks/baselines.json`.
6. Each rule carries a direction. An `ai-high` rule marks authorship, and a FAIL in the AI range says the text matches the AI pattern. A `human-high` rule is a form dial, and a FAIL there never claims authorship.
7. The summary compares no sample under 300 words.
8. Findings set the exit code. The band summary and the W-M10 density line are advisory.
9. The personal layer stays out of the package. Its rules are per-author.
10. The checks README tells a rule author to run a new rule over the audience's own writing first.

## Limits

1. The mechanical checks admitted the doc-shared AI corpora, so their rates read high by construction.
2. Some bands rest on two corpora per side, and the public doc-technical AI reference rests on one.
3. The band is a minimum and maximum over corpus-level rates, and no confidence interval. A new human corpus can widen it.
4. The doc-shared human band on W-M1 overlaps the AI reference, so the dash rule is weakest on letters and essays.
5. The low-rate lists W-M2, W-M3, W-M6, and W-M9 have no measurable band. Their evidence is the incidents they block.

## Appendix: references

- The source of the T-* rules: ASD (2021). Simplified Technical English, specification ASD-STE100, Issue 8. AeroSpace and Defence Industries Association of Europe.
- The tier 2 parser: spaCy, with the `en_core_web_sm` model. Honnibal, M., Montani, I., Van Landeghem, S., and Boyd, A. https://spacy.io
- The public chat dataset: Zhao, W., Ren, X., Hessel, J., Cardie, C., Choi, Y., and Deng, Y. (2024). WildChat: 1M ChatGPT interaction logs in the wild. ICLR 2024. Source of the frontier-model turns and the pre-2024 control.
