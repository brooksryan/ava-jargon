"""Fixtures for the suite.

The suite drives the installed `ava` script, not the source tree. `./test`
builds an image that installs the package with `uv tool install` and runs
pytest inside that install, so a failure here is a failure a user sees.

`AVA_BIN` names the script. Without it, the fixture takes the `ava` beside the
test interpreter, then the first `ava` on PATH.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _find_ava():
    named = os.environ.get("AVA_BIN")
    if named:
        return named
    sibling = Path(sys.executable).parent / "ava"
    if sibling.is_file():
        return str(sibling)
    found = shutil.which("ava")
    if found:
        return found
    pytest.exit("no `ava` script beside the interpreter or on PATH. Run ./test "
                "for the Docker suite, or venv/bin/pip install -e '.[dev]' for "
                "a local run.", returncode=2)


@pytest.fixture(scope="session")
def ava_bin():
    return _find_ava()


@pytest.fixture
def home(tmp_path):
    """A fresh HOME, so `-g` installs and ~/.ava never touch the real one."""
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture
def project(tmp_path):
    """An empty project directory; the default cwd for `ava`."""
    path = tmp_path / "project"
    path.mkdir()
    return path


@pytest.fixture
def ava(ava_bin, project, home):
    """Run `ava` with the given arguments; returns the CompletedProcess."""
    def run(*args, stdin=None, cwd=None):
        return subprocess.run([ava_bin, *args], cwd=cwd or project, input=stdin,
                              text=True, capture_output=True,
                              env={**os.environ, "HOME": str(home)})
    return run
