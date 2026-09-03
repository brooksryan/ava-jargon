# Voices

A voice is one JSON document you own by name. It records the surface and the extensions the mechanical check runs under, and a rubric a reviewer scores where mechanics cannot decide. [voice.schema.json](voice.schema.json) defines the shape, and `ava voice schema` prints it.

## Shape

| Field | Holds |
| --- | --- |
| `name` | the name you ask for the voice by: lowercase, digits, `. _ -` |
| `description` | one sentence: what the voice covers and who reads it |
| `surface` | `chat`, `doc-shared`, `doc-technical`, or `code` |
| `extend` | extension names whose vocabulary the audience accepts |
| `rules` | the rubric, one object per rule |

Each rule holds a `name`, a one-sentence `description`, observable `criteria`, a `scoring` structure, and a `requirement`:

- Pass-fail: `"scoring": {"type": "pass-fail"}` with `"requirement": {"pass": true}`.
- Scale: `"scoring": {"type": "scale", "min": 1, "max": 5, "anchors": {"1": "...", "5": "..."}}` with `"requirement": {"min": 4}`. Anchors are optional and keyed by the score.

## Commands

```bash
ava voice schema                    # the JSON schema
ava voice new NAME FILE             # create ~/.ava/voices/NAME.json from a JSON document; - reads stdin
ava voice new NAME FILE --project   # create .ava/voices/NAME.json in the project
ava voice list                      # every voice, project rows first
ava voice rubric NAME               # the rules as a reviewer reads them; --json prints the document
ava voice set NAME FILE             # merge a partial document: rules merge by name, other fields replace
ava voice rm NAME                   # delete the voice the name resolves to
ava check FILE --voice NAME         # the voice supplies --surface and --extend; an explicit flag overrides it
```

`new` and `set` validate the document against the schema. They refuse a document that misses the schema, name the failed field, and exit with code 2. The `new` command refuses a name that exists unless you pass `--force`.

## Where a voice lives

A personal voice lives in `~/.ava/voices/` (`AVA_HOME` moves it). A project voice lives in `.ava/voices/` in the working directory or a parent directory and travels with the repository. On a name clash ava uses the project voice. A path that ends in `.json` also names a voice.

## Gates

Both gate agents accept a voice by name. The gate runs the check under the voice and scores every rubric rule. It quotes the sentence that cost a score and fails the verdict when a rule misses its requirement. [skills/ava/references/voices.md](../../skills/ava/references/voices.md) gives an agent the steps to author one. This repository's issue voice is [.ava/voices/pm-issue.json](../../.ava/voices/pm-issue.json).
