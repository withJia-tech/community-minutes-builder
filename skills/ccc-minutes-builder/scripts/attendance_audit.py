#!/usr/bin/env python3
"""Compare a minutes attendance table with a confirmed evidence ledger.

Usage:
    python attendance_audit.py draft.docx --evidence attendance.json

The evidence JSON maps the three attendance categories to people. Each person
may be a name string or an object with `name` and optional `title` fields.
The script reports category counts, missing or extra people, duplicates,
spelling/capitalisation differences, category conflicts and title conflicts.
"""
import argparse
import json
import re
import sys
import zipfile

from lxml import etree


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
CATEGORIES = ('Present', 'Absent with Apologies', 'In Attendance')


def clean(value):
    return ' '.join(str(value or '').split())


def key(value):
    return clean(value).casefold()


def cell_text(cell):
    return clean(''.join(t.text or '' for t in cell.iter(W + 't')))


def load_tables(path):
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read('word/document.xml'))
    return root.find(W + 'body').findall(W + 'tbl')


def attendance_rows(path):
    tables = load_tables(path)
    if not tables:
        raise ValueError('document contains no tables')
    category_keys = {key(c): c for c in CATEGORIES}
    best = None
    best_score = -1
    for table in tables:
        text = key(' '.join(cell_text(c) for c in table.iter(W + 'tc')))
        score = sum(1 for category in category_keys if category in text)
        if score > best_score:
            best, best_score = table, score
    if best_score < 2:
        raise ValueError('could not identify the attendance table by its category headings')

    current = None
    people = []
    for tr in best.findall(W + 'tr'):
        cells = [cell_text(c) for c in tr.findall(W + 'tc')]
        # Header rows are short and person rows have 4 cells, so only a short
        # row can be a category header. A title such as "Grassroots Adviser
        # (present today)" must not switch the category.
        if len(cells) < 4:
            row_text = key(' '.join(cells))
            matched = [label for label in CATEGORIES if key(label) in row_text]
            if matched:
                current = matched[0]
                continue
        if current is None or len(cells) < 4:
            continue
        title, name = cells[1], cells[3]
        if name:
            people.append({'name': name, 'title': title, 'category': current})
    return people


def evidence_rows(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError('attendance evidence must be a JSON object')
    people = []
    for category in CATEGORIES:
        raw = data.get(category, [])
        if not isinstance(raw, list):
            raise ValueError('%s must be a list' % category)
        for person in raw:
            if isinstance(person, str):
                name, title = clean(person), ''
            elif isinstance(person, dict):
                name = clean(person.get('name'))
                title = clean(person.get('title'))
            else:
                raise ValueError('%s entries must be strings or objects' % category)
            if not name:
                raise ValueError('%s contains an entry without a name' % category)
            people.append({'name': name, 'title': title, 'category': category})
    return people


def index(people, side, blockers):
    out = {}
    for person in people:
        person_key = key(person['name'])
        if person_key in out:
            blockers.append('%s duplicates %r' % (side, person['name']))
        else:
            out[person_key] = person
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--evidence', required=True,
                    help='confirmed attendance JSON extracted from the current source')
    a = ap.parse_args()

    blockers = []
    try:
        actual_people = attendance_rows(a.docx)
        expected_people = evidence_rows(a.evidence)
    except (OSError, ValueError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        print('OVERALL VERDICT: FAIL')
        print('BLOCKER  %s' % exc)
        return 1

    actual = index(actual_people, 'minutes', blockers)
    expected = index(expected_people, 'evidence', blockers)

    print('| Category | Evidence | Minutes |')
    print('|---|---:|---:|')
    for category in CATEGORIES:
        want = sum(1 for p in expected_people if p['category'] == category)
        got = sum(1 for p in actual_people if p['category'] == category)
        print('| %s | %d | %d |' % (category, want, got))
        if want != got:
            blockers.append('%s count is %d in evidence but %d in minutes' %
                            (category, want, got))

    for person_key, want in expected.items():
        got = actual.get(person_key)
        if got is None:
            blockers.append('%r is in evidence but missing from minutes' % want['name'])
            continue
        if got['name'] != want['name']:
            blockers.append('minutes spell or capitalise %r as %r' %
                            (want['name'], got['name']))
        if got['category'] != want['category']:
            blockers.append('%r is %s in evidence but %s in minutes' %
                            (want['name'], want['category'], got['category']))
        if want['title'] and clean(got['title']) != want['title']:
            blockers.append('%r has title %r in evidence but %r in minutes' %
                            (want['name'], want['title'], got['title']))

    for person_key, got in actual.items():
        if person_key not in expected:
            blockers.append('%r appears in minutes but not in attendance evidence' %
                            got['name'])

    if blockers:
        print('\nOVERALL VERDICT: FAIL')
        for item in blockers:
            print('BLOCKER  %s' % item)
        return 1
    print('\nOVERALL VERDICT: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
