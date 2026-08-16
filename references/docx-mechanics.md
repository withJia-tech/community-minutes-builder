# Working on the .docx

Build on the previous month's file. Rebuilding from scratch loses the
letterhead image, the styles, the footer and the table geometry, and no
amount of care reproduces them exactly.

## The edit cycle

```bash
cp prev.docx base.docx
unzip -q base.docx -d unpacked
find unpacked -type l -delete
python /mnt/skills/public/docx/scripts/merge_runs.py unpacked/
# edit unpacked/word/document.xml with lxml — do not pretty-print
(cd unpacked && zip -Xrq ../out.docx .)
python /mnt/skills/public/docx/scripts/office/validate.py out.docx --original base.docx
```

`merge_runs.py` first, always. Word splits a visible sentence across many
runs, so the string you can see often does not exist contiguously in the XML.

Render and look at the result before handing it over:

```bash
python /mnt/skills/public/docx/scripts/office/soffice.py --headless --convert-to pdf out.docx
pdftoppm -jpeg -r 75 out.pdf page
```

## Structure of these minutes

Two tables in the body:

- **Table 0** — the attendance block. Rows: date/time, venue, a PRESENT
  header row, one row per person (4 cells: blank, appointment, colon, name),
  an ABSENT header row, more person rows, an IN ATTENDANCE header row, more
  person rows.
- **Table 1** — the numbered items. Three cells per row: number, content,
  action column.

To rebuild the roster: deep-copy a person row as a template, set cells 1 and
3, then remove all `<w:tr>` from the table and append the new sequence in
order. `tblPr` and `tblGrid` come before the rows, so appending is safe.

To reorder or renumber sections: collect the rows, build the new order as a
list of elements (reusing the same elements preserves all their content and
formatting), remove all rows, append in the new order, then set cell 0's
text to the new number.

## Setting cell text

Keep the first `<w:t>` in the paragraph — it carries the run's formatting —
set its text, and blank the rest. Set `xml:space="preserve"` when the string
has leading or trailing spaces.

Where a paragraph mixes bold and plain (an event title followed by a
description), split at the separator: keep the head in the original bold
run, deep-copy the run, strip `<w:b>` and `<w:bCs>` from the copy, put the
tail in it, and `addnext` it.

## Bullets

These files often have no bullet numbering defined — only decimal lists.
Add one abstract numbering definition with `numFmt` bullet, `lvlText`
`\uf0b7`, Symbol font, then reference it from a new `<w:num>`. Apply
`<w:numPr>` to each bullet paragraph, after `<w:pStyle>` if present.

Never type a literal bullet character. Typed bullets do not indent, do not
survive editing, and are immediately obvious to anyone who works in Word.

## Embedded table images

Finance and grant rows carry the tables as **images**, not editable text.
They must be replaced every month or the minutes silently report an old
period.

`scripts/swap_slide_images.py` handles this: it renders the relevant deck
page, crops the table, overwrites the media file, and recalculates the
drawing extent so the aspect ratio is preserved and nothing clips.

Find which relationship id sits in which row before swapping:

```python
blip = drawing.find('.//{...drawingml/2006/main}blip')
rid = blip.get('{...officeDocument/2006/relationships}embed')
```

Then map `rid` to `word/media/imageN.png` through
`word/_rels/document.xml.rels`.

Keep the width and scale the height: `cy = cx * (height / width)`. Set both
the `wp:extent` and every `a:ext` in the drawing, or Word and LibreOffice
disagree about the size.

## Column widths

If the numbering column is too narrow, numbers like `4.1.1` wrap onto two
lines and the document looks unproofed. Widen `tblGrid` and every cell's
`tcW`, and increase `tblW` to match — but check the total against the page
margins in `sectPr`, and re-render, because a wider table can clip the
embedded images at the right edge.

## What the linter checks

`scripts/lint_minutes.py` scans the document body, attendance content, headers,
footers, footnotes, endnotes and comments for leftover `[TBC]`, bracketed
editorial notes and other placeholders. It also reports empty spacer
paragraphs, action-column tags naming an agency that no longer appears in the
row, inconsistent month names, "as at" dates that did not move, identical
embedded images and repeated-word anomalies.

Pass `--profile committee-profile.json` to enforce approved committee terms,
proper-name spellings, aliases that must not appear, and nearby title/name
pairs. In `--final` mode, errors and warnings both return a non-zero status.
Treat that status as a failed signature-ready gate; do not suppress it by
removing evidence or placeholders that remain unresolved.
