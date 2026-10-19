#!/usr/bin/env python3
"""Replace a Word drawing's embedded table image with a cropped PDF slide.

The unpacked DOCX stays in an ignored working directory. Preview files are
written there too, not to a potentially tracked source-code directory.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PARSER = etree.XMLParser(resolve_entities=False, no_network=True)


def doc_path(unpacked):
    return Path(unpacked) / 'word' / 'document.xml'


def rels(unpacked):
    path = Path(unpacked) / 'word' / '_rels' / 'document.xml.rels'
    root = etree.parse(str(path), parser=PARSER).getroot()
    return {rel.get('Id'): rel.get('Target') for rel in root
            if rel.get('Type', '').endswith('/image')}


def checked_media_target(unpacked, raw_target):
    """Reject external or traversing relation targets before any file write."""
    if not raw_target or '://' in raw_target or raw_target.startswith('/'):
        raise ValueError('image relationship must reference a local media file')
    word = Path(unpacked).resolve() / 'word'
    media_dir = word / 'media'
    target = (word / raw_target).resolve()
    if media_dir != target.parent or target.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        raise ValueError('image relationship target must be a PNG/JPEG in word/media/')
    if not target.is_file():
        raise ValueError('referenced image does not exist: %s' % target.name)
    return target


def _drawings(tree, rid):
    matches = []
    for drawing in tree.getroot().iter(W + 'drawing'):
        blip = drawing.find('.//' + A + 'blip')
        if blip is None or blip.get(R + 'embed') != rid:
            continue
        extent = drawing.find('.//' + WP + 'extent')
        if extent is None or not extent.get('cx'):
            raise ValueError('drawing %s has no measurable width' % rid)
        matches.append((drawing, extent))
    if not matches:
        raise ValueError('relationship %s is not used by a document drawing' % rid)
    return matches


def cmd_inspect(args):
    tree = etree.parse(str(doc_path(args.unpacked)), parser=PARSER)
    rmap = rels(args.unpacked)
    body = tree.getroot().find(W + 'body')
    if body is None or not body.findall(W + 'tbl'):
        raise ValueError('DOCX document contains no minutes table')
    for tr in body.findall(W + 'tbl')[-1].findall(W + 'tr'):
        cells = tr.findall(W + 'tc')
        num = ''.join(t.text or '' for t in cells[0].iter(W + 't')).strip() if cells else '?'
        for drawing in tr.iter(W + 'drawing'):
            blip = drawing.find('.//' + A + 'blip')
            extent = drawing.find('.//' + WP + 'extent')
            if blip is not None:
                rid = blip.get(R + 'embed')
                print('row %-6s %-8s -> %s cx=%s cy=%s' % (
                    num or '?', rid, rmap.get(rid, '?'),
                    extent.get('cx') if extent is not None else '?',
                    extent.get('cy') if extent is not None else '?'))


def cmd_swap(args):
    from PIL import Image

    if args.page <= 0 or args.dpi <= 0:
        raise ValueError('page and dpi must be positive integers')
    if not (0 <= args.left < args.right <= 1 and
            0 <= args.top < args.bottom <= 1):
        raise ValueError('crop fractions must satisfy 0 <= left < right <= 1 and top < bottom')
    rmap = rels(args.unpacked)
    if args.rid not in rmap:
        raise ValueError('no image relationship %s in this document' % args.rid)
    target = checked_media_target(args.unpacked, rmap[args.rid])
    tree = etree.parse(str(doc_path(args.unpacked)), parser=PARSER)
    drawings = _drawings(tree, args.rid)

    with tempfile.TemporaryDirectory(prefix='ccc-slide-') as temp:
        stem = Path(temp) / 'slide'
        subprocess.run(['pdftoppm', '-r', str(args.dpi), '-f', str(args.page),
                        '-l', str(args.page), '-png', str(args.pdf), str(stem)],
                       capture_output=True, text=True, check=True)
        files = sorted(Path(temp).glob('slide*.png'))
        if len(files) != 1:
            raise ValueError('expected one rendered page but received %d' % len(files))
        with Image.open(files[0]) as rendered:
            width, height = rendered.size
            box = tuple(map(int, (width * args.left, height * args.top,
                                  width * args.right, height * args.bottom)))
            cropped = rendered.crop(box)
            if cropped.width < 1 or cropped.height < 1:
                raise ValueError('crop area was empty')
            extension = target.suffix.lower()
            fmt = 'JPEG' if extension in ('.jpg', '.jpeg') else 'PNG'
            staged_image = Path(temp) / ('replacement' + extension)
            cropped.convert('RGB').save(staged_image, format=fmt)
            preview = Path(args.preview).resolve() if args.preview else (
                Path(args.unpacked).resolve() / ('preview_%s.png' % args.rid))
            cropped.save(preview, format='PNG')
            ratio = cropped.height / cropped.width
        for drawing, extent in drawings:
            cx = int(extent.get('cx'))
            cy = int(round(cx * ratio))
            extent.set('cy', str(cy))
            for other in drawing.iter(A + 'ext'):
                other.set('cx', str(cx))
                other.set('cy', str(cy))
        staged_xml = Path(temp) / 'document.xml'
        tree.write(str(staged_xml), xml_declaration=True,
                   encoding='UTF-8', standalone=True)
        os.replace(staged_image, target)
        os.replace(staged_xml, doc_path(args.unpacked))
    print('replaced %s and updated drawing %s' % (target, args.rid))
    print('review preview: %s' % preview)


def main(argv=None):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('unpacked')
    inspect.set_defaults(func=cmd_inspect)
    swap = sub.add_parser('swap')
    swap.add_argument('unpacked')
    swap.add_argument('pdf')
    swap.add_argument('--page', type=int, required=True)
    swap.add_argument('--rid', required=True)
    swap.add_argument('--dpi', type=int, default=200)
    swap.add_argument('--top', type=float, default=0.13)
    swap.add_argument('--bottom', type=float, default=0.97)
    swap.add_argument('--left', type=float, default=0.02)
    swap.add_argument('--right', type=float, default=0.99)
    swap.add_argument('--preview', help='optional explicit preview output PNG path')
    swap.set_defaults(func=cmd_swap)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (OSError, ValueError, subprocess.CalledProcessError, etree.XMLSyntaxError) as exc:
        parser.exit(1, 'ERROR: %s\n' % exc)


if __name__ == '__main__':
    main()
