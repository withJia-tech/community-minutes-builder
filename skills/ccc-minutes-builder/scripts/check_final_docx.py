#!/usr/bin/env python3
"""Fail-closed guard for final*.docx in the designated output directory.

This PostToolUse check runs after a shell operation, so it cannot undo a
write. It rejects invalid inputs or unverifiable final files; it does not
replace attendance or source-map audit and does not certify document content.

By default only final*.docx immediately under the hook cwd are checked.
Set CCC_MINUTES_OUTPUT_DIR to a dedicated output directory when outputs live
elsewhere. This prevents stale files in unrelated subtrees from blocking work.
"""
import fnmatch
import json
import os
from pathlib import Path
import sys


def note(message):
    print('check_final_docx: %s' % message, file=sys.stderr)


def find_finals(directory):
    """Find only top-level final files; no recursive project-wide traversal."""
    return sorted(path for path in directory.iterdir() if path.is_file() and
                  fnmatch.fnmatch(path.name.lower(), 'final*.docx'))


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('hook payload must be a JSON object')
        cwd = payload.get('cwd')
        if not isinstance(cwd, str) or not cwd.strip():
            raise ValueError('hook payload must include a working directory')
        base = Path(cwd).resolve(strict=True)
        if not base.is_dir():
            raise ValueError('hook cwd is not a directory')
        configured = os.environ.get('CCC_MINUTES_OUTPUT_DIR')
        target = ((base / configured).resolve(strict=True) if configured and
                  not os.path.isabs(configured) else
                  Path(configured).resolve(strict=True) if configured else base)
        if not target.is_dir():
            raise ValueError('output directory is not a directory')
        finals = find_finals(target)
    except (OSError, ValueError, TypeError) as exc:
        note('cannot establish final-document scope: %s' % exc)
        return 2

    if not finals:
        return 0
    try:
        from docx_layout import load, minutes_rows
        from lint_minutes import unresolved_markers, visible_text
    except ImportError as exc:
        note('validation is unavailable (%s); final-document gate BLOCKED' % exc)
        return 2

    problems = []
    for path in finals:
        try:
            minutes_rows(load(path))
            markers = unresolved_markers(visible_text(path))
        except Exception as exc:
            problems.append((path.name, 'cannot validate DOCX: %s' % exc))
            continue
        if markers:
            problems.append((path.name, 'unresolved markers: %s' % ', '.join(markers[:10])))

    if problems:
        note('final-document gate FAILED; do not send these files for signature:')
        for filename, why in problems:
            note('  %s — %s' % (filename, why))
        note('Fix the underlying evidence or keep the document as a draft. '
             'Run attendance_audit.py, lint_minutes.py --final, and '
             'row_audit.py --source-map separately.')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
