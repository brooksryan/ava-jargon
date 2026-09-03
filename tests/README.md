# Tests

`./test` builds a Docker image and runs pytest inside it. The image installs the package with `uv tool install` from the working tree, the same path as the README. The suite therefore covers the wheel contents, the `ava` script, and every `ava setup` target.

| Command | Effect |
| --- | --- |
| `./test` | build the image, run every test |
| `./test -k setup` | pass the arguments after the `./test` flags to pytest |
| `./test --parser` | build the image with the `[parser]` extra and run the tier 2 tests |
| `./test --local` | run pytest from `./venv` against an editable install: `venv/bin/pip install -e '.[dev]'` |

| File | Covers |
| --- | --- |
| `test_checks.py` | the tier 1 checkers and the runner, as a library |
| `test_cli.py` | `ava check` exit codes, the linter line, `--json`, and the bundled lexicons |
| `test_setup.py` | each `ava setup` target, `-g`, `--force`, and the packaged assets against the repo files |
| `test_parser.py` | the tier 2 checkers; the module skips without spacy |

The tests call the installed `ava` script. Set `AVA_BIN` to test a different one.
