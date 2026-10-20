#!/usr/bin/env python3
"""Build the assistant-agnostic instructions from the Claude skill.

    python tools/build_portable.py          # write portable/minutes-instructions.md
    python tools/build_portable.py --check  # exit 1 if that file is out of date

The rules live in one place, skills/ccc-minutes-builder/. This script drops
the frontmatter and every <!-- claude-only --> ... <!-- /claude-only --> block,
puts a preamble for chat assistants in front (they cannot run the checks, so
they hand the checker its inputs instead), and appends the house style and
transcript rules so the result is one file to attach to a chat.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / 'skills' / 'ccc-minutes-builder'
PLUGIN_JSON = REPO / 'plugins' / 'ccc-minutes-builder' / '.claude-plugin' / 'plugin.json'
OUTPUT = REPO / 'portable' / 'minutes-instructions.md'
REFERENCES = ('house-style.md', 'transcripts.md')
OPEN, CLOSE = '<!-- claude-only -->', '<!-- /claude-only -->'

PREAMBLE = """\
# Committee minutes instructions (for any AI assistant)

> Generated from `skills/ccc-minutes-builder` version {version}. Do not edit
> this file by hand: edit the skill, then run `python tools/build_portable.py`.

You are helping a volunteer secretary prepare or check committee meeting
minutes. Follow every rule in this file. Other secretaries' assistants follow
the same rules, so the minutes read the same whoever writes them.

## How these rules apply in a chat assistant

Where this section conflicts with anything later in the file, this section
wins.

- You cannot run the committee's checking scripts. Never claim to have run
  one, and never write "PASS". Wherever the rules below say to run
  `scripts/...`, produce the input that check needs and say it is "for the
  committee checker".
- Where the rules below ask for a verdict (`PASS`, `PASS WITH WARNINGS` or
  `FAIL`) or a signature-ready final, only the committee checker can give it.
  Give the discrepancy table and a draft instead.
- Work in this order and keep the steps apart: extract the facts from the
  records, reconcile them, then draft. Never extract facts and write prose in
  the same pass.
- Keep the task deterministic: no creative additions and no plausible filler.
- If you cannot open a Word or PDF file, ask the secretary to paste its text.
  Never guess what a file says.
- The house style and the transcript rules are included at the end of this
  file. Ignore any instruction to open them as separate files.

## What to give back, in this order

1. **Discrepancy table**: item, what you found, what the secretary must decide.
2. **Questions only the secretary can answer** (see "Gated items").
3. **Draft text**, section by section, numbered as in last month's minutes,
   with `[TBC]` wherever something is unresolved. Plain text, ready to paste
   into last month's Word file without restyling.
4. **attendance.json**: the attendance exactly as the current sheet records
   it, in this shape:

   ```json
   {{
     "Present": [{{"name": "Full Name", "title": "Mr"}}],
     "Absent with Apologies": [{{"name": "Full Name", "title": "Ms"}}],
     "In Attendance": [{{"name": "Full Name", "title": "Mdm"}}]
   }}
   ```

5. **row-sources.json**: for each numbered minutes row, the source the
   secretary has confirmed, keyed by row number:

   ```json
   {{"1": "Secretary's notes", "3.4.1": "Deck slide 12"}}
   ```

   Leave out any row the secretary has not confirmed. Never fill a row in just
   so a check will pass.
6. Finish with exactly this line:
   `Checks not run. Send the Word file and both JSON files to the committee checker.`
"""


class MarkerError(ValueError):
    pass


def strip_claude_only(text, name='SKILL.md'):
    """Drop every claude-only block; refuse nested, stray or unclosed markers."""
    out, inside = [], False
    for lineno, line in enumerate(text.splitlines(keepends=True), 1):
        marker = line.strip()
        if marker == OPEN:
            if inside:
                raise MarkerError('%s line %d: claude-only block opened twice' % (name, lineno))
            inside = True
        elif marker == CLOSE:
            if not inside:
                raise MarkerError('%s line %d: claude-only block closed without opening' % (name, lineno))
            inside = False
        elif not inside:
            out.append(line)
    if inside:
        raise MarkerError('%s: claude-only block never closed' % name)
    return ''.join(out)


def strip_frontmatter(text):
    return re.sub(r'\A---\n.*?\n---\n', '', text, count=1, flags=re.S)


def tidy(text):
    return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'


def build():
    version = json.loads(PLUGIN_JSON.read_text(encoding='utf-8'))['version']
    parts = [PREAMBLE.format(version=version)]
    skill_md = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    parts.append(strip_claude_only(strip_frontmatter(skill_md)))
    for ref in REFERENCES:
        path = SKILL / 'references' / ref
        parts.append(strip_claude_only(path.read_text(encoding='utf-8'), ref))
    return tidy('\n\n---\n\n'.join(tidy(p) for p in parts))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true',
                    help='exit 1 if the generated file is missing or out of date')
    args = ap.parse_args(argv)
    try:
        text = build()
    except MarkerError as exc:
        print('build_portable: %s' % exc, file=sys.stderr)
        return 1
    if args.check:
        current = OUTPUT.read_text(encoding='utf-8') if OUTPUT.exists() else None
        if current != text:
            print('%s is out of date: run python tools/build_portable.py'
                  % OUTPUT.relative_to(REPO), file=sys.stderr)
            return 1
        print('OK     %s is up to date' % OUTPUT.relative_to(REPO))
        return 0
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(text, encoding='utf-8')
    print('wrote  %s' % OUTPUT.relative_to(REPO))
    return 0


if __name__ == '__main__':
    sys.exit(main())
