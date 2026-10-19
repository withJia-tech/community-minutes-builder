#!/usr/bin/env python3
"""Audit numbered minutes against independently confirmed source citations.

Keyword matching is for discovery only. A proposed deck slide never satisfies
this gate: a citation must be explicitly entered in --source-map by a reviewer.
"""
import argparse
import json
import re
import subprocess
import sys

from docx_layout import DocumentShapeError, read_rows
from lint_minutes import unresolved_markers

STOP = set('''the a an and or of to in for on at with by from is are was were
be been this that these those as it its their his her they he she we our
please refer more information slide deck report update shared presented
members committee meeting minutes will would also has have had not no'''.split())


def rows(path):
    return [(r.number, r.content, r.has_image) for r in read_rows(path)]


def deck_pages(pdf):
    try:
        info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True,
                              text=True, check=True).stdout
        match = re.search(r'^Pages:\s+(\d+)\s*$', info, re.M)
        if match is None or int(match.group(1)) < 1:
            raise ValueError('pdfinfo did not report a positive slide count')
        pages = []
        for p in range(1, int(match.group(1)) + 1):
            result = subprocess.run(['pdftotext', '-f', str(p), '-l', str(p),
                                     str(pdf), '-'], capture_output=True,
                                    text=True, errors='replace', check=True)
            pages.append(' '.join(result.stdout.split()))
        return pages
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        raise ValueError('cannot extract deck pages: %s' % exc) from exc


def keywords(text, k=8):
    words = re.findall(r"[A-Za-z][A-Za-z'&-]{3,}", text)
    seen, out = set(), []
    for word in words:
        lower = word.lower()
        if lower in STOP or lower in seen:
            continue
        seen.add(lower)
        out.append(word)
        if len(out) >= k:
            break
    return out


def best_page(text, pages):
    kws = keywords(text)
    if not kws or not pages:
        return None, 0
    best, score = None, 0
    for index, page in enumerate(pages, 1):
        low = page.lower()
        score_here = sum(1 for kw in kws if kw.lower() in low)
        if score_here > score:
            best, score = index, score_here
    return best, score / len(kws)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('docx')
    parser.add_argument('--deck', help='meeting slide deck PDF')
    parser.add_argument('--previous', help='previous approved minutes')
    parser.add_argument('--source-map', help='JSON mapping row numbers to confirmed citations')
    args = parser.parse_args(argv)
    try:
        current_rows = rows(args.docx)
        pages = deck_pages(args.deck) if args.deck else []
        previous = {n: t for n, t, _ in rows(args.previous)} if args.previous else {}
        with open(args.source_map, encoding='utf-8') if args.source_map else _empty_source_map() as fh:
            confirmed = json.load(fh)
        if not isinstance(confirmed, dict):
            raise ValueError('source map must be a JSON object keyed by row number')
    except (DocumentShapeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print('OVERALL VERDICT: FAIL')
        print('BLOCKER  %s' % exc)
        return 1

    blockers, warnings = [], []
    seen_rows = set()
    print('| Row | Content (start) | Suggested source (not evidence) | Confirmed source | Signal |')
    print('|---|---|---|---|---|')
    for num, content, has_image in current_rows:
        seen_rows.add(num)
        page, confidence = best_page(content, pages)
        suggestion = 'Deck slide %d' % page if page else '—'
        if page and confidence < 0.4:
            suggestion += ' (weak)'
        source = confirmed.get(num)
        if not isinstance(source, str) or not source.strip():
            source = '**UNCONFIRMED**'
            blockers.append('row %s has no confirmed source' % num)
        else:
            source = source.strip()
        signals = []
        if has_image:
            signals.append('has embedded image — confirm current reporting period')
        if previous.get(num, '').strip() == content.strip() and content.strip() and num in previous:
            signals.append('**identical to last month**')
        markers = unresolved_markers(content)
        if markers:
            signals.append('unresolved marker')
            blockers.append('row %s carries an unresolved marker: %s' % (num, ', '.join(markers)))
        if not content.strip() and has_image:
            signals.append('image only')
        snippet = content[:60] + '…' if len(content) > 60 else content
        print('| %s | %s | %s | %s | %s |' % (
            num, snippet.replace('|', '/'), suggestion, source.replace('|', '/'),
            '; '.join(signals)))

    print()
    if pages:
        thin = [index for index, page in enumerate(pages, 1) if len(page.split()) < 12]
        if thin:
            print('Image-heavy slides requiring manual visual inspection: %s' %
                  ', '.join(map(str, thin)))
            warnings.append('image-heavy slides require visual source checking')
        matched = {page for _, content, _ in current_rows
                   for page, conf in [best_page(content, pages)]
                   if page is not None and conf >= 0.2}
        unmatched = [index for index in range(1, len(pages) + 1)
                     if index not in matched and index not in thin]
        if unmatched:
            print('Slides with no matching row — confirm each was either covered '
                  'elsewhere or genuinely not tabled: %s' % ', '.join(map(str, unmatched)))
            warnings.append('one or more deck slides have no matching minute row')
        print()
    unused = sorted(set(confirmed) - seen_rows)
    if unused:
        warnings.append('source map contains rows absent from the draft: %s' % ', '.join(unused))
    print('Automated suggestions are not citations. Review current evidence and '
          'enter each confirmed citation in --source-map.')
    verdict = 'FAIL' if blockers else ('PASS WITH WARNINGS' if warnings else 'PASS')
    print('\nOVERALL VERDICT: %s' % verdict)
    for item in blockers:
        print('BLOCKER  %s' % item)
    for item in warnings:
        print('WARN     %s' % item)
    return 1 if blockers else 0


def _empty_source_map():
    """Return a context-manager-compatible empty JSON map when omitted."""
    from io import StringIO
    return StringIO('{}')


if __name__ == '__main__':
    sys.exit(main())
