# Voices

A voice is one JSON document you own by name. It records the checks that run, the band table and lexicon they run against, the extensions the audience accepts, and a rubric a reviewer scores where mechanics cannot decide. [voice.schema.json](../../fixtures/voices/voice.schema.json) defines the shape, and `ava voice schema` prints it.

## Shape

| Field | Holds |
| --- | --- |
| `name` | the name you ask for the voice by: lowercase, digits, `. _ -` |
| `description` | one sentence: what the voice covers and who reads it |
| `checks` | the mechanical checks that run, by id, such as `W-M1` |
| `bands` | the band table the summary compares rates against; `ava bands list` names them |
| `lexicon` | a shipped lexicon name such as `universal-code`, or a path to a lexicon file; absent, the universal lexicon named after the bands |
| `extend` | extension names whose vocabulary the audience accepts |
| `rubric` | the rubric, one object per rule |

Each rubric rule holds a `name`, a one-sentence `description`, observable `criteria`, a `scoring` structure, and a `requirement`:

- Pass-fail: `"scoring": {"type": "pass-fail"}` with `"requirement": {"pass": true}`.
- Scale: `"scoring": {"type": "scale", "min": 1, "max": 5, "anchors": {"1": "...", "5": "..."}}` with `"requirement": {"min": 4}`. Anchors are optional and keyed by the score.

A file from before this shape, with `surface` and `rules`, still loads: `surface` reads as `bands`, `rules` as `rubric`, and the checks come from the rule set the surface implied. `ava voice set` writes the new keys back.

## Shipped voices

| Voice | Checks | Bands | Lexicon |
| --- | --- | --- | --- |
| `westinghouse` | the 9 Westinghouse rules | `chat` | `universal-chat` |
| `shared-docs` | the same 9 | `doc-shared` | `universal-doc-shared` |
| `technical-docs` | the 21 technical rules | `doc-technical` | `universal-doc-technical` |
| `code` | the same 21 | `code` | `universal-code` |

A shipped voice carries no rubric. Copy one under a new name to add a rubric: `ava voice rubric code --json` prints the document.

## Commands

```bash
ava voice schema                    # the JSON schema
ava voice new NAME FILE             # create ~/.ava/voices/NAME.json from a JSON document; - reads stdin
ava voice new NAME FILE --project   # create .ava/voices/NAME.json in the project
ava voice new NAME FILE --checks technical   # seed the checks from a rule set when the document names none
ava voice list                      # every voice, project rows first
ava voice rubric NAME               # the settings and the rules as a reviewer reads them; --json prints the document
ava voice set NAME checks +W-M11 -T-M3       # add and drop rule ids; bare ids replace the list
ava voice set NAME bands code       # bands, lexicon, and description take one value; extend takes ids like checks
ava voice set NAME FILE             # merge a partial document: rubric rules merge by name, other fields replace
ava voice rm NAME                   # delete the voice the name resolves to
ava check FILE --voice NAME         # the voice supplies --rules, --bands, --lexicon, and --extend; an explicit flag overrides it
```

`new` and `set` validate the document against the schema. They refuse a document that misses the schema, name the failed field, and exit with code 2. They also refuse a rule id no checker carries and a band table no file carries. The `new` command refuses a name that exists unless you pass `--force`.

`set` can edit a personal copy of a shipped voice. Removing that copy resets it: the next normal command restores the default. Both commands refuse files inside the package.

## Where a voice lives

The first normal command copies shipped voices from the package into `~/.ava/voices/` (`AVA_HOME` moves it). Custom personal voices live there too. A project voice lives in `.ava/voices/` in the working directory or a parent directory and travels with the repository. A name resolves project first, then personal, then packaged. A path that ends in `.json` also names a voice.

## Gates

Both gate agents accept a voice by name. The gate runs the check under the voice and scores every rubric rule. It quotes the sentence that cost a score and fails the verdict when a rule misses its requirement. [skills/ava/references/voices.md](../../skills/ava/references/voices.md) gives an agent the steps to author one.
