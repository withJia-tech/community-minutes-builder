#!/usr/bin/env python3
"""Crop a table off a slide and drop it into a minutes cell, replacing the
image that is already there.

Inspect first, to see which relationship id sits in which row:

    python swap_slide_images.py inspect unpacked/

Then swap, one pair at a time:

    python swap_slide_images.py swap unpacked/ deck.pdf --page 66 --rid rId8

The crop defaults trim the slide's title banner and footer decoration; adjust
with --top/--bottom/--left/--right (fractions of the page) and check the
saved preview before rezipping.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def doc_path(unpacked):
    return os.path.join(unpacked, 'word', 'document.xml')


def rels(unpacked):
    path = os.path.join(unpacked, 'word', '_rels', 'document.xml.rels')
    root = etree.parse(path).getroot()
    out = {}
    for rel in root:
        if rel.get('Type', '').endswith('/image'):
            out[rel.get('Id')] = rel.get('Target')
    return out


def cmd_inspect(a):
    tree = etree.parse(doc_path(a.unpacked))
    rmap = rels(a.unpacked)
    tbl = tree.getroot().find(W + 'body').findall(W + 'tbl')[-1]
    for tr in tbl.findall(W + 'tr'):
        cells = tr.findall(W + 'tc')
        if not cells:
            continue
        num = ''.join(t.text or '' for t in cells[0].iter(W + 't')).strip()
        for d in tr.iter(W + 'drawing'):
            blip = d.find('.//' + A + 'blip')
            ext = d.find('.//' + WP + 'extent')
            rid = blip.get(R + 'embed')
            print('row %-6s %-8s -> %-20s cx=%s cy=%s'
                  % (num or '?', rid, rmap.get(rid, '?'),
                     ext.get('cx'), ext.get('cy')))


def cmd_swap(a):
    from PIL import Image
    rmap = rels(a.unpacked)
    if a.rid not in rmap:
        sys.exit('no image relationship %s in this document' % a.rid)
    target = os.path.join(a.unpacked, 'word', rmap[a.rid])

    tmp = tempfile.mkdtemp()
    stem = os.path.join(tmp, 'pg')
    subprocess.run(['pdftoppm', '-r', str(a.dpi), '-f', str(a.page),
                    '-l', str(a.page), '-png', a.pdf, stem], check=True)
    rendered = [os.path.join(tmp, f) for f in sorted(os.listdir(tmp))
                if f.endswith('.png')]
    if not rendered:
        sys.exit('pdftoppm produced nothing for page %d' % a.page)

    im = Image.open(rendered[0])
    w, h = im.size
    box = (int(w * a.left), int(h * a.top), int(w * a.right), int(h * a.bottom))
    crop = im.crop(box)
    crop.save(target)
    preview = os.path.join(os.getcwd(), 'preview_%s.png' % a.rid)
    crop.save(preview)

    ratio = crop.size[1] / crop.size[0]
    tree = etree.parse(doc_path(a.unpacked))
    hit = False
    for d in tree.getroot().iter(W + 'drawing'):
        blip = d.find('.//' + A + 'blip')
        if blip is None or blip.get(R + 'embed') != a.rid:
            continue
        hit = True
        ext = d.find('.//' + WP + 'extent')
        cx = int(ext.get('cx'))
        cy = int(round(cx * ratio))
        ext.set('cy', str(cy))
        for e in d.iter(A + 'ext'):
            e.set('cx', str(cx))
            e.set('cy', str(cy))
    if not hit:
        sys.exit('relationship %s is declared but not used in the body' % a.rid)
    tree.write(doc_path(a.unpacked), xml_declaration=True,
               encoding='UTF-8', standalone=True)
    print('wrote %s (%dx%d) and rescaled %s' % (target, crop.size[0],
                                                crop.size[1], a.rid))
    print('preview saved to %s — look at it before rezipping' % preview)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)

    i = sub.add_parser('inspect')
    i.add_argument('unpacked')
    i.set_defaults(func=cmd_inspect)

    s = sub.add_parser('swap')
    s.add_argument('unpacked')
    s.add_argument('pdf')
    s.add_argument('--page', type=int, required=True)
    s.add_argument('--rid', required=True)
    s.add_argument('--dpi', type=int, default=200)
    s.add_argument('--top', type=float, default=0.13)
    s.add_argument('--bottom', type=float, default=0.97)
    s.add_argument('--left', type=float, default=0.02)
    s.add_argument('--right', type=float, default=0.99)
    s.set_defaults(func=cmd_swap)

    a = ap.parse_args()
    a.func(a)


if __name__ == '__main__':
    main()
