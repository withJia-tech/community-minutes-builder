#!/usr/bin/env python3
"""Row-by-row audit table for a minutes draft.

    python row_audit.py draft.docx --deck slides.pdf --previous june.docx

Emits a markdown table of every numbered row with a suggested source and any
carry-over signal. The suggested source is a keyword match and is meant to be
checked by a person, not trusted — an empty Source column is the point of the
exercise, not a defect in the script.
"""
import argparse
import json
import re
import subprocess
import zipfile
from lxml import etree

from lint_minutes import unresolved_markers

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
STOP = set('''the a an and or of to in for on at with by from is are was were
be been this that these those as it its their his her they he she we our
please refer more information slide deck report update shared presented
members committee meeting minutes will would also has have had not no'''.split())


def rows(path):
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read('word/document.xml'))
    tbl = root.find(W + 'body').findall(W + 'tbl')[-1]
    out = []
    for tr in tbl.findall(W + 'tr'):
        cells = tr.findall(W + 'tc')
        if len(cells) < 3:
            continue
        vals = [''.join(t.text or '' for t in c.iter(W + 't')) for c in cells]
        has_img = tr.find('.//' + W + 'drawing') is not None
        out.append((vals[0].strip(), ' '.join(vals[1].split()), has_img))
    return out


def deck_pages(pdf):
    pages = []
    n = 0
    info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    m = re.search(r'Pages:\s+(\d+)', info)
    if m:
        n = int(m.group(1))
    for p in range(1, n + 1):
        txt = subprocess.run(
            ['pdftotext', '-f', str(p), '-l', str(p), pdf, '-'],
            capture_output=True, text=True, errors='replace').stdout
        pages.append(' '.join(txt.split()))
    return pages


def keywords(text, k=8):
    words = re.findall(r"[A-Za-z][A-Za-z'&-]{3,}", text)
    seen, out = set(), []
    for w in words:
        lw = w.lower()
        if lw in STOP or lw in seen:
            continue
        seen.add(lw)
        out.append(w)
        if len(out) >= k:
            break
    return out


def best_page(text, pages):
    kws = keywords(text)
    if not kws or not pages:
        return None, 0
    best, score = None, 0
    for i, page in enumerate(pages, 1):
        low = page.lower()
        s = sum(1 for k in kws if k.lower() in low)
        if s > score:
            best, score = i, s
    return best, score / max(len(kws), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--deck', help='meeting slide deck PDF')
    ap.add_argument('--previous', help='previous month\'s minutes, to spot carry-over')
    ap.add_argument('--source-map', help='JSON object mapping row numbers to confirmed source citations')
    a = ap.parse_args()

    pages = deck_pages(a.deck) if a.deck else []
    prev = {n: t for n, t, _ in rows(a.previous)} if a.previous else {}
    confirmed = {}
    if a.source_map:
        with open(a.source_map, encoding='utf-8') as f:
            confirmed = json.load(f)
        if not isinstance(confirmed, dict):
            raise SystemExit('source map must be a JSON object keyed by row number')

    blockers, warnings = [], []
    seen_rows = set()

    print('| Row | Content (start) | Suggested source | Signal |')
    print('|---|---|---|---|')
    for num, text, has_img in rows(a.docx):
        if not text.strip() and not has_img:
            continue
        if not num:
            continue
        seen_rows.add(num)
        page, conf = best_page(text, pages)
        if num in confirmed and str(confirmed[num]).strip():
            source = str(confirmed[num]).strip()
        elif page and conf >= 0.4:
            source = 'Deck slide %d' % page
            warnings.append('row %s has only an automated source suggestion' % num)
        elif page and conf >= 0.2:
            source = 'Deck slide %d (weak)' % page
            warnings.append('row %s has only a weak automated source suggestion' % num)
        else:
            source = '**none found**'
            blockers.append('row %s has no confirmed source' % num)
        signals = []
        if has_img:
            signals.append('has embedded image — confirm it was replaced')
        old = prev.get(num, '')
        if old and text.strip() and old.strip() == text.strip():
            signals.append('**identical to last month**')
        # same markers as lint_minutes.py, so a citation such as [1] passes
        # here exactly as it passes the linter
        markers = unresolved_markers(text)
        if markers:
            signals.append('unresolved marker')
            blockers.append('row %s carries an unresolved marker: %s'
                            % (num, ', '.join(markers)))
        if not text.strip() and has_img:
            signals.append('image only')
        snippet = (text[:60] + '…') if len(text) > 60 else text
        print('| %s | %s | %s | %s |'
              % (num, snippet.replace('|', '/'), source, '; '.join(signals)))

    print()
    if pages:
        thin = [i for i, p in enumerate(pages, 1) if len(p.split()) < 12]
        if thin:
            print('Slides carrying almost no extractable text (mostly images, '
                  'so keyword matching cannot see them — check these by eye): %s'
                  % ', '.join(map(str, thin)))
            warnings.append('image-heavy slides require visual source checking')
        matched = set()
        for num, text, _ in rows(a.docx):
            if num:
                pg, conf = best_page(text, pages)
                if pg and conf >= 0.2:
                    matched.add(pg)
        unmatched = [i for i in range(1, len(pages) + 1)
                     if i not in matched and i not in thin]
        if unmatched:
            print('Slides with no matching row — confirm each was either '
                  'covered elsewhere or genuinely not tabled: %s'
                  % ', '.join(map(str, unmatched)))
            warnings.append('one or more deck slides have no matching minute row')
        print()
    unused = sorted(set(map(str, confirmed)) - seen_rows)
    if unused:
        warnings.append('source map contains rows absent from the draft: %s' %
                        ', '.join(unused))
    print('Fill the Source column by hand where it says none found. A row with '
          'no source in the deck must trace to the annexes or to the '
          "secretary's notes, or it should not be in the minutes. Keyword "
          'matching is a prompt for the eye, not a verdict.')
    if blockers:
        verdict = 'FAIL'
    elif warnings:
        verdict = 'PASS WITH WARNINGS'
    else:
        verdict = 'PASS'
    print('\nOVERALL VERDICT: %s' % verdict)
    for item in blockers:
        print('BLOCKER  %s' % item)
    for item in warnings:
        print('WARN     %s' % item)
    return 1 if blockers else 0


if __name__ == '__main__':
    raise SystemExit(main())
