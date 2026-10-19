"""Fail-closed parsing and structural checks for the supported committee DOCX layout.

The gate deliberately supports the documented attendance + numbered-items
format, not arbitrary Word documents. Unsupported layouts require human review.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import zipfile
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NUMBER = re.compile(r'\d+(?:\.\d+)*')
CATEGORIES = ('Present', 'Absent with Apologies', 'In Attendance')


class DocumentShapeError(ValueError):
    """The file cannot be verified against the supported minutes layout."""


@dataclass(frozen=True)
class MinuteRow:
    number: str
    content: str
    action: str
    has_image: bool


def cell_text(cell):
    """Join Word text runs without inserting spaces inside split words."""
    return ''.join(t.text or '' for t in cell.iter(W + 't'))


def load(path):
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read('word/document.xml')
        root = etree.fromstring(raw, parser=etree.XMLParser(resolve_entities=False, no_network=True))
    except (OSError, KeyError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        raise DocumentShapeError('unreadable DOCX package: %s' % exc) from exc
    if root.find(W + 'body') is None:
        raise DocumentShapeError('DOCX has no document body')
    return root


def _body_tables(root):
    body = root.find(W + 'body')
    if body is None:
        raise DocumentShapeError('DOCX has no document body')
    tables = body.findall(W + 'tbl')
    if len(tables) < 2:
        raise DocumentShapeError('expected an attendance table and a separate minutes table')
    return tables


def _check_attendance(table):
    seen = set()
    people = 0
    for tr in table.findall(W + 'tr'):
        cells = tr.findall(W + 'tc')
        vals = [' '.join(cell_text(c).split()).casefold() for c in cells]
        if len(cells) < 4:
            for label in CATEGORIES:
                if label.casefold() in ' '.join(vals):
                    seen.add(label)
        elif len(cells) >= 4 and vals[3]:
            people += 1
    if len(seen) < 2 or not people:
        raise DocumentShapeError('attendance table missing category headings or named attendees')


def minutes_rows(root):
    """Return validated rows; reject missing, duplicate or unnumbered content.

    Only the direct child tables in the document body are used. Nested tables
    within minute cells are not accidentally treated as the main minutes table.
    """
    tables = _body_tables(root)
    _check_attendance(tables[0])
    table = tables[-1]
    result = []
    seen = set()
    for position, tr in enumerate(table.findall(W + 'tr'), 1):
        cells = tr.findall(W + 'tc')
        if len(cells) != 3:
            raise DocumentShapeError('minutes row %d must have exactly 3 cells' % position)
        num, content, action = (cell_text(c).strip() for c in cells)
        has_image = (tr.find('.//' + W + 'drawing') is not None or
                     tr.find('.//' + W + 'pict') is not None)
        if not any((num, content, action, has_image)):
            continue
        # The standard table may include a single header row.
        if position == 1 and num.casefold() in {'item', 'no.', 'no', 'number'}:
            continue
        if not NUMBER.fullmatch(num):
            raise DocumentShapeError('minutes row %d has substantive content but invalid/missing number %r' % (position, num))
        if num in seen:
            raise DocumentShapeError('duplicate minutes row number %s' % num)
        if not content.strip() and not has_image:
            raise DocumentShapeError('minutes row %s has no text or image' % num)
        seen.add(num)
        result.append(MinuteRow(num, ' '.join(content.split()), action, has_image))
    if not result:
        raise DocumentShapeError('minutes table contains no substantive numbered rows')
    return result


def read_rows(path):
    return minutes_rows(load(path))
