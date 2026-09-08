# Teach ava a voice

A voice is one JSON document. It records the checks that run, the band table and lexicon they run against, and the extensions the audience accepts. It also records a rubric a gate scores where the mechanical check cannot decide. `ava voice schema` prints the shape. Never write the file by hand.

## Shape

| Field | Holds |
| --- | --- |
| `name` | the name you ask for the voice by: lowercase, digits, `. _ -` |
| `description` | one sentence: what the voice covers and who reads it |
| `checks` | the rule ids that run; `ava voice new NAME FILE --checks SET` seeds them from a rule set |
| `bands` | the band table: `chat`, `doc-shared`, `doc-technical`, or `code`; the routing table in SKILL.md maps a document to one |
| `lexicon` | a shipped lexicon name such as `universal-code`, or a path; absent, the universal lexicon named after the bands |
| `extend` | extension names whose vocabulary the audience accepts; `ava jargon extensions` lists them |
| `rubric` | the rubric, one object per rule |

Each rule holds a `name`, a one-sentence `description`, two to four observable `criteria`, a `scoring` structure, and a `requirement`:

- Pass-fail: `"scoring": {"type": "pass-fail"}`, `"requirement": {"pass": true}`. Use it for a rule a reader settles with yes or no.
- Scale: `"scoring": {"type": "scale", "min": 1, "max": 5, "anchors": {"1": "...", "3": "...", "5": "..."}}`, `"requirement": {"min": 4}`. Use it for a rule of degree. Write an anchor for the low, the middle, and the top score.

## Create a voice

1. Run `ava voice list`. If the name exists, go to "Edit a voice".
2. Ask the person three things: the kind of document, who reads it, and personal or shared with the project.
3. Ask for the rules one at a time. For each rule, draft the name, the description, the criteria, the scoring, and the requirement.
4. Show the draft rule. Confirm it before you ask for the next rule.
5. Write the document to a temp file.
6. Run `ava voice new NAME FILE`. Add `--project` for a shared voice.
7. On exit code 2, read the field the error names, fix the document, and run again.
8. Run `ava voice rubric NAME`. Show the output to the person as the last step.

## Edit a voice

`ava voice set NAME FILE` merges a partial document. Rules merge by name; other fields replace. To change one rule, send only that rule with its name. `ava voice rm NAME` removes a voice.

## Write a rule a reviewer can score

- Make each criterion observable in the text, for example "No sentence names a technology." Avoid a vague criterion such as "Sounds product-minded."
- Put one idea in each criterion.
- Set the requirement at the standard the person meets in their own writing.
- Keep the rubric to four rules or fewer.
- Before you trust a rule, score a sample of the person's own writing with it. A rule that fails often on the person is a wrong rule for that person.

## Use a voice

- Mechanical check: `ava check FILE --voice NAME`. The voice supplies the checks, the bands, the lexicon, and the extensions; an explicit flag wins.
- Gate review: name the voice in the invocation of `ava-prose-gate` or `ava-technical-gate`. The gate scores every rule and fails the verdict when a rule misses its requirement.
