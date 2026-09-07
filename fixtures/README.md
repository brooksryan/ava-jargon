# Shipped fixtures

`fixtures/` holds the data and setup text that every installation receives. The package exposes these files under `ava_jargon.fixtures`.

| Directory or file | Contents |
| --- | --- |
| `lexicons/` | shared vocabulary |
| `bands/` | comparison ranges and their schema |
| `voices/` | shipped voices and their schema |
| `config.schema.json` | the settings schema |
| `name_stoplist.txt` | the default name stoplist |
| `assets/` | gate agents, the skill, its references, and the gate contract |

The plugin entries under `agents/` and `skills/`, and the root gate contract, link to the maintained files here. The installed package contains regular files.

Tests create their examples in temporary directories. Private research inputs stay in the ignored `corpus/`, `audit/`, and workspace `lexicons/` directories. The package data list in `pyproject.toml` selects the distributed fixtures. The archive tests verify their contents.
