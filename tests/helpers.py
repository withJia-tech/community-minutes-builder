"""Shared paths and helpers for the test suite."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
SKILL = REPO / 'skills' / 'ccc-minutes-builder'
SCRIPTS = SKILL / 'scripts'

if str(FIXTURES) not in sys.path:
    sys.path.insert(0, str(FIXTURES))

needs_poppler = pytest.mark.skipif(
    shutil.which('pdftotext') is None or shutil.which('pdfinfo') is None,
    reason='poppler-utils (pdftotext, pdfinfo) not installed')


def run_script(name, *args, stdin=None, env=None):
    """Run one skill script as a subprocess, the way a user would."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name)] + [str(a) for a in args],
        input=stdin, capture_output=True, text=True, timeout=60, env=env)


def lines(result):
    return result.stdout.splitlines()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return path
