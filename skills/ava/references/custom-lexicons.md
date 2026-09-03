# Build a custom lexicon

The jargon scorer (W-M10, `ava jargon score`) compares text to a lexicon. A lexicon comes from two corpora: the **approved** side is the audience's own vocabulary; the **contrast** side is the kind of writing you test. Terms common in the contrast side but absent from the approved side become jargon. The shipped `universal-*` lexicons cover generic surfaces. Build your own for a specific audience: a customer, a team, or a community.

## Collect the corpora

1. Create one directory per side, for example `corpus/customer-slack/` and `corpus/our-drafts/`.
2. Save one document per `.txt` file. The CLI reads `**/*.txt` under each directory.
3. Collect at least 30,000 tokens per side. The CLI warns below that floor because keyness gets noisy.
4. Prefer many short documents over few long ones. The dispersion test counts how many documents contain each term, so one long document weakens it.
5. Write a `README.md` in each corpus directory. Record the source and the filters you applied, so the lexicon stays auditable.

## Build

```
ava jargon build corpus/APPROVED corpus/CONTRAST -o /abs/path/lexicons/my-lexicon.json
```

Each side accepts several directories, comma-separated. Pass an absolute `-o` path: the default resolves against your current directory.

## Extend a shipped lexicon instead

When the shipped lexicon fits but marks words your audience does use, add an extension. The `ava jargon extend NAME PATH...` command profiles one more approved corpus into `~/.ava/extensions/NAME.json` (`AVA_HOME` moves it). The profile holds term counts, not text.

1. Collect the audience's own writing as a directory of `.txt` or `.md` files. A `.json` or `.jsonl` export also works, one document per record, with `--field` for the text field (default `text`).
2. Pass `--split blank` when one file holds many messages with a blank line between them, `--split line` for one message per line, or `-` to read stdin.
3. The 30,000-token floor from step 3 above applies.
4. Read the extend output: it lists how many terms the extension vetoes from each shipped lexicon, and the first few.

```
ava jargon extend my-prompts prompts.jsonl --note "typed prompts, all projects"
ava check spec.md --rules technical --extend my-prompts
ava jargon score spec.md -l lexicons/universal-doc-technical.json --extend my-prompts
```

`--extend` overlays the extension on the lexicon in use. An extension adds to the approved side only. Every term the corpus uses in more than its dispersion share of documents joins the approved vocabulary, so the lexicon stops counting it as jargon. Pass the flag once per extension.

`ava jargon extensions` lists the profiles on this machine. The stderr line `extend: NAME (N vetoed, M added)` confirms the overlay. Pass `--extend` on every `ava check` that should use it. The gate agents accept an extension input and add the flag from it; they never pick one themselves.

## Use

```
ava jargon score draft.md -l my-lexicon.json          # density + coverage, --json for machines
ava jargon delta before/ after/ -l my-lexicon.json    # A vs B with a bootstrap CI
ava check draft.md --surface chat --lexicon my-lexicon.json   # overrides the auto-loaded universal lexicon
```

## Record it

Keep one row per lexicon in a `lexicons/README.md`: file name, approved side, contrast side, purpose.

## Trust, then use

Before you trust a lexicon or a rule, run it over your own writing. A term or rule that fires often on you is wrong for you - recalibrate the corpora.
