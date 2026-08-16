#!/usr/bin/env python3
"""Formatting and staleness linter for CCC minutes drafts.

    python lint_minutes.py draft.docx
    python lint_minutes.py draft.docx --previous june.docx --period June --month July

Report problems grouped by severity. Draft mode returns non-zero for errors.
Final mode also treats warnings as a failed signature-ready gate.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
PLACEHOLDERS = [r'\[TBC\]', r'\[time\]', r'\[name[^\]]*\]', r'\[n\]',
                r'\[to complete\]', r'\[TO BE COMPLETED[^\]]*\]', r'\bTBD\b']


def load(path):
    with zipfile.ZipFile(path) as z:
        return etree.fromstring(z.read('word/document.xml'))


def visible_text(path):
    """Return text from all Word parts that can carry visible or review text."""
    parts = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if re.fullmatch(
                     r'word/(document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml',
                     n)]
        for name in names:
            root = etree.fromstring(z.read(name))
            text = ' '.join((t.text or '').strip() for t in root.iter(W + 't'))
            parts.append('%s\n%s' % (name, text))
    return '\n'.join(parts)


def load_profile(path):
    if not path:
        return {}
    with open(path, encoding='utf-8') as f:
        profile = json.load(f)
    if not isinstance(profile, dict):
        raise ValueError('profile must be a JSON object')
    return profile


def media(path):
    out = {}
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.startswith('word/media/'):
                out[n] = hashlib.sha256(z.read(n)).hexdigest()
    return out


def rows(root):
    """Yield (number, text, action) for every row of the numbered-item table."""
    tables = root.find(W + 'body').findall(W + 'tbl')
    if len(tables) < 2:
        return
    for tr in tables[-1].findall(W + 'tr'):
        cells = tr.findall(W + 'tc')
        if len(cells) < 3:
            continue
        vals = [''.join(t.text or '' for t in c.iter(W + 't')) for c in cells]
        yield vals[0].strip(), vals[1], vals[2].strip()


def para_stats(root):
    empty = 0
    for tc in root.iter(W + 'tc'):
        paras = tc.findall(W + 'p')
        if len(paras) < 2:
            continue
        for p in paras:
            has_img = (p.find('.//' + W + 'drawing') is not None
                       or p.find('.//' + W + 'pict') is not None)
            txt = ''.join(t.text or '' for t in p.iter(W + 't')).strip()
            if not txt and not has_img:
                empty += 1
    return empty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--previous', help='previous month\'s minutes, for image comparison')
    ap.add_argument('--period', help='month the minutes report on, e.g. June')
    ap.add_argument('--month', help='month of the meeting itself, e.g. July')
    ap.add_argument('--profile', help='JSON file of approved terms, names and titles')
    ap.add_argument('--final', action='store_true',
                    help='treat placeholders, profile violations and warnings as final-gate failures')
    a = ap.parse_args()

    root = load(a.docx)
    body_rows = list(rows(root))
    full = visible_text(a.docx)
    profile = load_profile(a.profile)
    errors, warnings, notes = [], [], []

    # placeholders across the entire Word package, not only the minutes table
    for pat in PLACEHOLDERS:
        hits = list(re.finditer(pat, full, re.I))
        if hits:
            msg = 'document carries %d placeholder(s) matching %r' % (
                len(hits), hits[0].group(0))
            (errors if a.final else warnings).append(msg)

    # bracketed editorial notes
    for m in re.finditer(r'\[[^\]]{4,}\]', full):
        if not re.match(r'\[(TBC|time|n)\]', m.group(0), re.I):
            msg = 'document carries a possible editorial note: %s' % m.group(0)[:70]
            (errors if a.final else notes).append(msg)

    # deterministic wording, spelling and title checks from an approved profile
    replacements = profile.get('term_replacements', {})
    if not isinstance(replacements, dict):
        errors.append('profile term_replacements must be an object')
        replacements = {}
    for wrong, right in replacements.items():
        if wrong and re.search(re.escape(wrong), full, re.I):
            msg = 'unapproved term or spelling %r; approved form is %r' % (wrong, right)
            (errors if a.final else warnings).append(msg)

    people = profile.get('people', [])
    if not isinstance(people, list):
        errors.append('profile people must be a list')
        people = []
    for person in people:
        if not isinstance(person, dict) or not person.get('name'):
            errors.append('each profile person needs a canonical name')
            continue
        name = str(person['name'])
        aliases = person.get('aliases', [])
        titles = person.get('titles', [])
        for alias in aliases:
            if alias and re.search(r'(?<!\w)%s(?!\w)' % re.escape(str(alias)), full, re.I):
                msg = 'unapproved name spelling %r; canonical name is %r' % (alias, name)
                (errors if a.final else warnings).append(msg)
        hit = re.search(r'(?<!\w)%s(?!\w)' % re.escape(name), full, re.I)
        if hit and titles:
            context = full[max(0, hit.start() - 160):hit.end() + 80]
            if not any(re.search(re.escape(str(title)), context, re.I)
                       for title in titles):
                msg = '%r appears without an approved nearby title (%s)' % (
                    name, ', '.join(map(str, titles)))
                (errors if a.final else warnings).append(msg)

    for m in re.finditer(r'\b([A-Za-z]{2,})\s+\1\b', full, re.I):
        warnings.append('possible duplicated word %r' % m.group(0))

    # empty spacer paragraphs
    n_empty = para_stats(root)
    if n_empty:
        warnings.append('%d empty paragraph(s) inside table cells — these show '
                        'as gaps in the rendered document' % n_empty)

    # stale months
    if a.period:
        stale = [m for m in MONTHS
                 if m != a.period and m != (a.month or '')
                 and re.search(r'\b%s 20\d\d\b' % m, full)]
        # only complain about months earlier than the reporting period
        if a.period in MONTHS:
            idx = MONTHS.index(a.period)
            earlier = [m for m in stale if MONTHS.index(m) < idx]
            for m in earlier:
                warnings.append('%s appears in the body — confirm it is a '
                                'deliberate carry-forward and not a figure that '
                                'should have been refreshed to %s'
                                % (m, a.period))

    # "as at" dates
    for num, text, _ in body_rows:
        for m in re.finditer(r'as at ([^),.]{4,30})', text, re.I):
            notes.append('row %s says "as at %s" — confirm the date moved'
                         % (num or '?', m.group(1).strip()))

    # action column tags naming an agency absent from the row
    action_tags = profile.get('action_tags',
                              ['NPC', 'LTA', 'HDB', 'NEA', 'CCKTC', 'FSC'])
    if not isinstance(action_tags, list):
        errors.append('profile action_tags must be a list')
        action_tags = []
    action_pattern = (r'\b(%s)\b' % '|'.join(
        re.escape(str(tag)) for tag in action_tags if str(tag))) if action_tags else None
    for num, text, action in body_rows:
        for tag in re.findall(action_pattern, action) if action_pattern else []:
            if tag not in text:
                warnings.append('row %s action column is tagged %s but the row '
                                'does not mention %s — likely carried over'
                                % (num or '?', tag, tag))

    # unchanged images
    if a.previous:
        now, before = media(a.docx), media(a.previous)
        same = [k for k, v in now.items() if before.get(k) == v]
        # letterhead is expected to be identical; table images are not
        if len(same) > 1:
            warnings.append('%d embedded image(s) are byte-identical to the '
                            'previous minutes — check the finance and grant '
                            'tables were actually replaced' % len(same))

    # numbering continuity
    seen = [n for n, _, _ in body_rows if re.fullmatch(r'\d+', n or '')]
    expected = [str(i) for i in range(1, len(seen) + 1)]
    if seen != expected:
        warnings.append('top-level numbering is %s — expected %s'
                        % (', '.join(seen), ', '.join(expected)))

    for label, items in (('ERROR', errors), ('WARN', warnings), ('NOTE', notes)):
        for i in items:
            print('%-6s %s' % (label, i))
    if not (errors or warnings or notes):
        print('OK     nothing flagged')
    return 1 if errors or (a.final and warnings) else 0


if __name__ == '__main__':
    sys.exit(main())
