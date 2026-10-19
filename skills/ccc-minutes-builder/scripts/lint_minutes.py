#!/usr/bin/env python3
"""DOCX structure, terminology, placeholders, recency and formatting gate.

Final mode blocks structural defects, unresolved markers and warnings.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile

from lxml import etree
from docx_layout import DocumentShapeError, W, load, minutes_rows

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
PLACEHOLDERS = [r'\[TBC\]', r'\[time\]', r'\[name[^\]]*\]', r'\[n\]',
                r'\[to complete\]', r'\[TO BE COMPLETED[^\]]*\]', r'\bTBD\b']
EDITORIAL_NOTE = r'\[[^\]]{4,}\]'
NOTE_EXEMPT = r'\[(TBC|time|n)\]'


def unresolved_markers(text):
    spans = set()
    for pat in PLACEHOLDERS:
        spans.update(m.span() for m in re.finditer(pat, text, re.I))
    for match in re.finditer(EDITORIAL_NOTE, text):
        if not re.match(NOTE_EXEMPT, match.group(0), re.I):
            spans.add(match.span())
    outer = [s for s in spans if not any(
        o != s and o[0] <= s[0] and s[1] <= o[1] for o in spans)]
    return [text[a:b] for a, b in sorted(outer)]


def visible_text(path):
    """Read text across runs and paragraphs while preserving word boundaries.

    Word often splits a word across multiple runs. Runs are concatenated;
    paragraphs receive a space to avoid merging adjacent unrelated words.
    """
    parts = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if re.fullmatch(
                r'word/(document|header\d+|footer\d+|footnotes|endnotes|comments)\.xml',
                name)]
            if 'word/document.xml' not in names:
                raise DocumentShapeError('DOCX is missing word/document.xml')
            for name in names:
                root = etree.fromstring(archive.read(name), parser=etree.XMLParser(
                    resolve_entities=False, no_network=True))
                paragraphs = []
                for para in root.iter(W + 'p'):
                    paragraphs.append(''.join(t.text or '' for t in para.iter(W + 't')))
                # Important: do not join separate runs with spaces.
                parts.append(name + '\n' + ' '.join(paragraphs))
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        raise DocumentShapeError('unreadable DOCX text: %s' % exc) from exc
    return '\n'.join(parts)


def load_profile(path):
    if not path:
        return {}
    with open(path, encoding='utf-8') as fh:
        profile = json.load(fh)
    if not isinstance(profile, dict):
        raise ValueError('profile must be a JSON object')
    return profile


def media(path):
    out = {}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.startswith('word/media/'):
                out[name] = hashlib.sha256(archive.read(name)).hexdigest()
    return out


def rows(root):
    for item in minutes_rows(root):
        yield item.number, item.content, item.action


def para_stats(root):
    empty = 0
    for tc in root.iter(W + 'tc'):
        paras = tc.findall(W + 'p')
        if len(paras) < 2:
            continue
        for para in paras:
            has_image = (para.find('.//' + W + 'drawing') is not None or
                         para.find('.//' + W + 'pict') is not None)
            txt = ''.join(t.text or '' for t in para.iter(W + 't')).strip()
            if not txt and not has_image:
                empty += 1
    return empty


def _first_body_mention(rows, name):
    """Locate the first substantive mention, ignoring the attendance roster."""
    regex = re.compile(r'(?<!\w)%s(?!\w)' % re.escape(name), re.I)
    for row in rows:
        match = regex.search(row.content)
        if match:
            # Return the same row, so a title in the attendance table or an
            # unrelated neighbouring row cannot satisfy this person's title.
            return row.number, row.content, match
    return None


def _title_near_mention(content, match, titles):
    # Titles must directly precede the name (allow punctuation/whitespace),
    # not appear incidentally anywhere within a broad character window.
    prefix = content[:match.start()]
    return any(re.search(r'(?<!\w)%s[\s,.:;-]*$' % re.escape(str(title)),
                         prefix, re.I) for title in titles if str(title).strip())


def _stale_period_mentions(full, period, meeting_month, report_year):
    """Produce warning messages for earlier reported periods (including Dec→Jan)."""
    if period not in MONTHS:
        return []
    if meeting_month and meeting_month not in MONTHS:
        return []
    messages = []
    pat = r'\b(%s)\s+(20\d{2})\b' % '|'.join(MONTHS)
    found = {(m.group(1), int(m.group(2))) for m in re.finditer(pat, full)}
    for month, year in sorted(found, key=lambda x: (x[1], MONTHS.index(x[0]))):
        if report_year is not None:
            if (year, MONTHS.index(month)) >= (report_year, MONTHS.index(period)):
                continue
        elif MONTHS.index(month) >= MONTHS.index(period):
            continue
        # A historic month/year is not proof of stale data; require review.
        messages.append('%s %s appears in the document — confirm it is a deliberate '
                        'historical reference and not stale %s data' % (
                            month, year, period))
    return messages


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--previous', help='previous approved minutes')
    ap.add_argument('--period', help='reporting period month, e.g. January')
    ap.add_argument('--month', help='meeting month, e.g. February')
    ap.add_argument('--report-year', type=int, help='reporting year (required for Dec→Jan detection)')
    ap.add_argument('--profile', help='approved names, terms and titles JSON')
    ap.add_argument('--final', action='store_true')
    a = ap.parse_args(argv)

    try:
        root = load(a.docx)
        body_rows = minutes_rows(root)
        full = visible_text(a.docx)
        profile = load_profile(a.profile)
    except (DocumentShapeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print('ERROR  %s' % exc)
        return 1
    errors, warnings, notes = [], [], []

    for pat in PLACEHOLDERS:
        hits = list(re.finditer(pat, full, re.I))
        if hits:
            msg = 'document carries %d placeholder(s) matching %r' % (
                len(hits), hits[0].group(0))
            (errors if a.final else warnings).append(msg)
    for hit in re.finditer(EDITORIAL_NOTE, full):
        if not re.match(NOTE_EXEMPT, hit.group(0), re.I):
            msg = 'document carries a possible editorial note: %s' % hit.group(0)[:70]
            (errors if a.final else notes).append(msg)

    replacements = profile.get('term_replacements', {})
    if not isinstance(replacements, dict):
        errors.append('profile term_replacements must be an object')
        replacements = {}
    for wrong, right in replacements.items():
        if wrong and re.search(r'(?<!\w)%s(?!\w)' % re.escape(str(wrong)), full, re.I):
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
        if not isinstance(aliases, list) or not isinstance(titles, list):
            errors.append('aliases and titles must be lists for %s' % name)
            continue
        for alias in aliases:
            if alias and re.search(r'(?<!\w)%s(?!\w)' % re.escape(str(alias)), full, re.I):
                msg = 'unapproved name spelling %r; canonical name is %r' % (alias, name)
                (errors if a.final else warnings).append(msg)
        first = _first_body_mention(body_rows, name)
        if first and titles and not _title_near_mention(first[1], first[2], titles):
            msg = '%r first appears in minutes row %s without an approved title (%s)' % (
                name, first[0], ', '.join(map(str, titles)))
            (errors if a.final else warnings).append(msg)

    for m in re.finditer(r'\b([A-Za-z]{2,})\s+\1\b', full, re.I):
        warnings.append('possible duplicated word %r' % m.group(0))
    n_empty = para_stats(root)
    if n_empty:
        warnings.append('%d empty paragraph(s) inside table cells — these show '
                        'as gaps in the rendered document' % n_empty)

    warnings.extend(_stale_period_mentions(full, a.period, a.month, a.report_year))
    for item in body_rows:
        for m in re.finditer(r'as at ([^),.]{4,30})', item.content, re.I):
            (warnings if a.final else notes).append(
                'row %s says "as at %s" — confirm the date moved' %
                (item.number, m.group(1).strip()))

    # action column tags naming an agency absent from the row. The agencies
    # differ by committee, so the list comes from the profile; with no
    # profile entry nothing is checked.
    action_tags = profile.get('action_tags', [])
    if not isinstance(action_tags, list):
        errors.append('profile action_tags must be a list')
        action_tags = []
    action_pattern = (r'\b(%s)\b' % '|'.join(
        re.escape(str(tag)) for tag in action_tags if str(tag))) if action_tags else None
    for item in body_rows:
        for tag in re.findall(action_pattern, item.action) if action_pattern else []:
            if tag not in item.content:
                warnings.append('row %s action column is tagged %s but the row '
                                'does not mention %s — likely carried over' %
                                (item.number, tag, tag))

    if a.previous:
        try:
            before, now = media(a.previous), media(a.docx)
        except (OSError, zipfile.BadZipFile) as exc:
            print('ERROR  cannot check previous file media: %s' % exc)
            return 1
        common = [name for name, digest in now.items() if before.get(name) == digest]
        if len(common) > 1:
            warnings.append('%d embedded image(s) are byte-identical to the '
                            'previous minutes — check finance and grant tables' % len(common))

    top_levels = [r.number for r in body_rows if re.fullmatch(r'\d+', r.number)]
    expected = [str(index) for index in range(1, len(top_levels) + 1)]
    if top_levels != expected:
        warnings.append('top-level numbering is %s — expected %s' %
                        (', '.join(top_levels), ', '.join(expected)))

    for label, entries in (('ERROR', errors), ('WARN', warnings), ('NOTE', notes)):
        for entry in entries:
            print('%-6s %s' % (label, entry))
    if not (errors or warnings or notes):
        print('OK     nothing flagged')
    return 1 if errors or (a.final and warnings) else 0


if __name__ == '__main__':
    sys.exit(main())
