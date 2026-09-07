# Lexicons

A lexicon compares two corpora. The **approved** side is the audience's own vocabulary. The **contrast** side is the writing under test. A term the contrast side overuses, and the audience says in at most 1 document in 100, is jargon. The `ava jargon score` command reports three classes for a file or a corpus. The `ava check` command reports the same numbers on the W-M10 advisory line.

| Class | Definition | Where it lives |
| --- | --- | --- |
| jargon | a term the contrast corpus overuses against the audience, past every build threshold | the `jargon` list in the lexicon file |
| approved | every content term the audience used 3 or more times in 2 or more documents, plus every name on the stoplist | the `approved_vocabulary` list in the lexicon file |
| unapproved | a content word or bigram in neither list; a word must also sit under the Zipf gate, and neither may hold a digit or a stoplist name | computed by the scorer per document |

Every rate divides by content words, the tokens left after the function-word list. The lexicon file records that list under `meta.stopwords`. Unapproved measures distance from the audience. It cannot show who wrote a document: text from another company scores high on it too.

## Shipped lexicons

`ava check` picks the universal lexicon the voice names, or the one named after the bands, when the caller passes no `--lexicon`.

| File | Approved side (the audience) | Contrast side (scored against) | Surface |
| --- | --- | --- | --- |
| universal-chat.json | Hacker News comments, Ubuntu IRC, W3C mail, Enron (pre-2022) | generated Claude chat + 2024 GPT-4 turns | chat |
| universal-doc-shared.json | shareholder letters, startup essays, investor memos, longform journalism, software-magazine articles, plain-language guides, Wikipedia (pre-2022) | AI blogposts + AI marketing (post-2024) | doc-shared |
| universal-doc-technical.json | RFCs, PostgreSQL/Django/Rust docs, arXiv, distill.pub, SRE book (pre-2022) | AI-agent-authored GitHub docs (post-2024) | doc-technical |
| universal-code.json | GitHub READMEs + comments (pre-2022) | AI-agent-authored READMEs + comments (post-2024) | code |

The AI corpora write about AI, so terms such as `claude`, `ai`, and `seo` top these lists. Only the density signal separates the sides, so W-M10 is advisory.

The maintained lexicons live in [`fixtures/lexicons/`](../../fixtures/lexicons/). Both a checkout and an installed command read this data.

## Score and compare

```bash
ava jargon score draft.md -l fixtures/lexicons/universal-code.json   # the three classes and coverage for one file
ava jargon score corpus/dir -l LEXICON --top 20                  # one row per document
ava jargon delta before/ after/ -l LEXICON                       # A versus B density per class, with a bootstrap CI
```

Add `--json` to either command for one object instead of text.

## Extend a lexicon

`ava jargon extend NAME PATH...` profiles one more approved corpus into `~/.ava/extensions/NAME.json` (`AVA_HOME` moves it). `--extend NAME` on `ava check`, `ava jargon score`, or `ava jargon delta` overlays it on the lexicon in use. The flag repeats.

```bash
ava jargon extend my-prompts prompts.jsonl --field text --note "typed prompts"
ava check spec.md --voice technical-docs --extend my-prompts
ava jargon extensions                                            # the profiles on this machine
```

An extension adds to the approved side only. Every term the corpus uses in more than its dispersion share of documents joins the approved vocabulary, so the lexicon stops counting it as jargon. The build prints how many terms the extension vetoes from each shipped lexicon.

Sources: `.txt` and `.md` files count one document each. The build removes fenced and inline code from `.md` files; `--keep-code` keeps it. A `.json` or `.jsonl` file counts one document per record, and `--field` names the text field. `--split blank` or `--split line` cuts one file into many documents. `-` reads stdin. Collect 30k+ tokens.

## Build a lexicon

One document per `.txt` file, 30k+ tokens per side:

```bash
ava jargon build corpus/AUDIENCE corpus/YOURS -o /abs/path/lexicons/mine.json
```

Each side accepts several directories, comma-separated. Pass an absolute `-o` path. `ava jargon build -h` lists the keyness thresholds: the Dunning G2 floor, the Hardie log-ratio floor, the dispersion floors, and the Zipf gate. Before you trust a lexicon, score a sample of the audience's own writing with it. High density there marks a wrong lexicon for that audience. [The lexicon study](../../research/lexicons.md) gives the method, the value of each threshold, and the evidence behind it.
