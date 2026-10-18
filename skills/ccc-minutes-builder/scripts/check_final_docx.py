#!/usr/bin/env python3
"""Claude Code hook: nothing bracketed reaches the Chairman.

The plugin runs this after every Bash tool call (PostToolUse). It reads the
hook payload from stdin, takes the working folder from its `cwd`, and looks
there for Word files named final*.docx. Each one is checked with
lint_minutes.unresolved_markers(): the same [TBC], [time], TBD and bracketed
editorial-note patterns the linter reports. A citation such as [1] is not a
marker.

Exit 2 when a final still carries a marker. Claude Code sends the stderr
message back to Claude, so the final cannot quietly go out for signature.
Exit 0 otherwise. Drafts are never checked: they carry [TBC] legitimately
until Phase 4.

The hook fails open. Bad input, a missing lxml or an unreadable file prints a
note and exits 0, so a broken check never blocks unrelated work.

Try it by hand:

    echo '{"cwd": "."}' | python3 check_final_docx.py; echo $?
"""
import fnmatch
import json
import os
import sys

SKIP_DIRS = {'node_modules', '__pycache__', 'unpacked'}


def note(message):
    print('check_final_docx: %s' % message, file=sys.stderr)


def find_finals(root):
    """Yield every final*.docx under root, skipping tool and dot folders."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in SKIP_DIRS)
        for name in sorted(filenames):
            if fnmatch.fnmatch(name.lower(), 'final*.docx'):
                yield os.path.join(dirpath, name)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError as exc:
        note('could not read the hook input as JSON (%s); skipping' % exc)
        return 0
    if not isinstance(payload, dict):
        note('hook input is not a JSON object; skipping')
        return 0
    cwd = payload.get('cwd') or os.getcwd()
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        note('working folder %r not found; skipping' % (cwd,))
        return 0

    finals = list(find_finals(cwd))
    if not finals:
        return 0

    try:
        from lint_minutes import unresolved_markers, visible_text
    except ImportError as exc:
        note('cannot load lint_minutes (%s); skipping' % exc)
        return 0

    problems = []
    for path in finals:
        try:
            markers = unresolved_markers(visible_text(path))
        except Exception as exc:  # fail open: an unreadable file is not a verdict
            note('could not read %s (%s); skipping' % (path, exc))
            continue
        if markers:
            problems.append((os.path.relpath(path, cwd), markers))

    if not problems:
        return 0
    print('Nothing bracketed reaches the Chairman: these final minutes still '
          'carry unresolved markers.', file=sys.stderr)
    for path, markers in problems:
        shown = ', '.join(markers[:10])
        if len(markers) > 10:
            shown += ', and %d more' % (len(markers) - 10)
        print('  %s: %s' % (path, shown), file=sys.stderr)
    print('Resolve each item with the drafter and then remove its marker, or '
          'leave the document as a draft (not named final*.docx) with the '
          'blocker named. Never delete a marker only to pass this check '
          '(SKILL.md, Phase 4).', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
