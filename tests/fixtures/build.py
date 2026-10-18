"""Build synthetic minutes fixtures at test time.

The repository ignores *.docx and *.pdf so that real meeting records cannot
be committed by accident. Tests therefore generate their binaries here, into
pytest's tmp_path, from plain Python data that is easy to read in a diff.

Everything is standard library only and deterministic: the same input always
produces byte-identical files.

DOCX layout (the pattern the scripts expect):
  * table 0 is attendance: single-cell category header rows, then 4-cell
    person rows [n, title, '', name];
  * the last table holds the numbered items: 3-cell rows [num, text, action].
"""
import zipfile
from xml.sax.saxutils import escape

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
FIXED_DATE = (1980, 1, 1, 0, 0, 0)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>')

ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
    'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '</Relationships>')

# --- the synthetic committee -------------------------------------------------
# All names are invented. Categories follow the house attendance form.

ATTENDANCE = [
    ('Present', [('Mdm', 'Alice Lim'),
                 ('Mr', 'Benjamin Tan'),
                 ('Ms', 'Chloe Ng')]),
    ('Absent with Apologies', [('Mr', 'David Ong')]),
    ('In Attendance', []),
]

DRAFT_ITEMS = [
    ('1', 'Confirmation of Minutes. Chairman Alice Lim invited members to '
          'confirm the minutes of the last meeting, which were confirmed '
          'without amendment.', ''),
    ('2', 'Environment. The NEA officer shared that dengue cases around '
          'Block 123 Example Avenue had fallen. Residents asked for more '
          'frequent checks of stagnant water at the void deck.', 'NEA'),
    ('3', "Chairman's Report. Mdm Alice Lim thanked Mr Benjamin Tan and "
          'Ms Chloe Ng for organising the lantern walk.', ''),
    ('4', 'Any Other Matters. There being no other matters, the meeting '
          'ended after the announcements.', ''),
]

PREVIOUS_ITEMS = [
    ('1', 'Confirmation of Minutes. Chairman Alice Lim invited members to '
          'confirm the minutes of the last meeting, which were confirmed '
          'without amendment.', ''),
    ('2', 'Environment. The NEA officer reported a dengue cluster around '
          'Block 123 Example Avenue.', 'NEA'),
    ('3', "Chairman's Report. Mdm Alice Lim welcomed new members.", ''),
]

DECK_SLIDES = [
    # Slide 1 matches item 2 of the draft.
    'Environment Update. Dengue cases around Block 123 Example Avenue have '
    'fallen this month. Officers will continue checks of stagnant water at '
    'the void deck with residents.',
    # Slide 2 matches no item: it should be reported as unmatched.
    'Youth Network Carnival. Volunteers proposed a football clinic, a '
    'badminton league and a bicycle safety course for teenagers during the '
    'December school holidays.',
]


# --- DOCX ----------------------------------------------------------------------

def _para(text='', drawing=False):
    runs = ''
    if text:
        runs += '<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % escape(text)
    if drawing:
        runs += '<w:r><w:drawing/></w:r>'
    return '<w:p>%s</w:p>' % runs


def _cell(text='', drawing=False):
    return '<w:tc>%s</w:tc>' % _para(text, drawing)


def _row(cells):
    return '<w:tr>%s</w:tr>' % ''.join(cells)


def attendance_table(attendance):
    """attendance: [(category, [(title, name), ...]), ...]"""
    rows = []
    for category, people in attendance:
        rows.append(_row([_cell(category)]))
        for n, (title, name) in enumerate(people, 1):
            rows.append(_row([_cell(str(n)), _cell(title), _cell(), _cell(name)]))
    return '<w:tbl>%s</w:tbl>' % ''.join(rows)


def items_table(items):
    """items: [(num, text, action), ...] or (num, text, action, has_image)."""
    rows = []
    for item in items:
        num, text, action = item[:3]
        drawing = bool(item[3]) if len(item) > 3 else False
        rows.append(_row([_cell(num), _cell(text, drawing), _cell(action)]))
    return '<w:tbl>%s</w:tbl>' % ''.join(rows)


def document_xml(attendance, items, heading='Minutes of the Example Gardens CCC Meeting'):
    body = (_para(heading) + attendance_table(attendance) + _para()
            + items_table(items) + '<w:sectPr/>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="%s"><w:body>%s</w:body></w:document>'
            % (W_NS, body))


def _write_zip(path, members):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in members:
            info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return path


def build_docx(path, attendance=None, items=None, **kwargs):
    attendance = ATTENDANCE if attendance is None else attendance
    items = DRAFT_ITEMS if items is None else items
    return _write_zip(path, [
        ('[Content_Types].xml', CONTENT_TYPES),
        ('_rels/.rels', ROOT_RELS),
        ('word/document.xml', document_xml(attendance, items, **kwargs)),
    ])


# --- PDF -----------------------------------------------------------------------

def _pdf_escape(text):
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _wrap(text, width=70):
    lines, line = [], ''
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = (line + ' ' + word).strip()
    if line:
        lines.append(line)
    return lines


def build_pdf(path, slides=None):
    """Write a minimal PDF 1.4 deck: one Helvetica text page per slide."""
    slides = DECK_SLIDES if slides is None else slides
    n = len(slides)
    page_ids = [4 + 2 * i for i in range(n)]
    objects = {
        1: '<< /Type /Catalog /Pages 2 0 R >>',
        2: '<< /Type /Pages /Kids [%s] /Count %d >>' % (
            ' '.join('%d 0 R' % p for p in page_ids), n),
        3: '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    }
    for i, slide in enumerate(slides):
        page_id, content_id = page_ids[i], page_ids[i] + 1
        ops = ['BT', '/F1 14 Tf', '16 TL', '50 550 Td']
        for line in _wrap(slide):
            ops.append('(%s) Tj T*' % _pdf_escape(line))
        ops.append('ET')
        stream = '\n'.join(ops).encode('latin-1')
        objects[page_id] = (
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 720 600] '
            '/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>' % content_id)
        objects[content_id] = (
            b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream')

    out = bytearray(b'%PDF-1.4\n')
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        body = objects[num]
        if isinstance(body, str):
            body = body.encode('latin-1')
        out += b'%d 0 obj\n' % num + body + b'\nendobj\n'
    xref = len(out)
    size = max(objects) + 1
    out += b'xref\n0 %d\n0000000000 65535 f \n' % size
    for num in range(1, size):
        out += b'%010d 00000 n \n' % offsets[num]
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (size, xref)
    with open(path, 'wb') as f:
        f.write(bytes(out))
    return path


def build_all(directory):
    """Write previous.docx, draft.docx and deck.pdf into directory."""
    return {
        'previous': build_docx(directory / 'previous.docx', items=PREVIOUS_ITEMS),
        'draft': build_docx(directory / 'draft.docx'),
        'deck': build_pdf(directory / 'deck.pdf'),
    }
