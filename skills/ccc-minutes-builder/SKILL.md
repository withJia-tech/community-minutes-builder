---
name: ccc-minutes-builder
description: "Build or audit signature-ready Citizens' Consultative Committee (CCC) and grassroots committee monthly minutes in Word. Use for drafting minutes from source records or checking attendance, official names and titles, terminology, dates, figures, slide-to-row coverage, stale carry-forwards, embedded tables, placeholders, spelling and formatting. Trigger for CCC or grassroots minutes even when the files have generic or misleading names; reconciliation and source traceability are mandatory outcomes."
---

# CCC minutes builder

Minutes are a signed official record. The failure that matters is not a slow
draft — it is a fluent draft that asserts something nobody said, or carries
last month's figures forward under this month's date. Everything below is
arranged so the drafter sees what is uncertain before they see a polished
paragraph.

## Required outcome

Produce three things:

1. a draft or signature-ready minutes document, as requested;
2. a discrepancy list naming every unresolved attendance, source, term, title,
   date, figure or formatting issue; and
3. a row-by-row source audit with an overall verdict: `PASS`,
   `PASS WITH WARNINGS`, or `FAIL`.

Never label an output final or signature-ready while any blocking item remains.
Do not add background knowledge, plausible connective detail, inferred views or
events that are absent from the supplied records.

## Runtime requirements

Use a filesystem, Python with `lxml` and Pillow, Poppler tools such as
`pdftoppm` and `pdftotext`, and an available DOCX editing and rendering
toolchain. Discover the DOCX helpers available in the current runtime rather
than assuming a helper path exists.

## Model and generation policy

Keep this task deterministic. If generation controls are available, use a low
temperature (`0` to `0.2`). If model selection is available and the user has
not requested a model, run the complete workflow on a Sonnet-class model first.
Do not recommend or switch to an Opus-class model merely because there are many
files or the minutes are long.

Use an Opus-class model only when the user requests it, or after a complete
Sonnet pass leaves a named material blocker involving unreadable evidence,
irreconcilable cross-source conflict, or semantic source matching that cannot
be resolved by the deterministic checks. State the failed check and the reason
an escalation may help. If the runtime does not expose model or temperature
controls, continue conservatively and do not claim that either was set.

Use the same fixed sequence on smaller models: preflight, extract, reconcile,
draft, lint, render, row audit. Do not combine extraction and prose generation
in one pass.

Read `references/house-style.md` before writing any prose, and
`references/docx-mechanics.md` before touching the .docx.

## Step 0 — Preflight the request and inputs

Before reading for content, reduce the user's request to this checklist:

| Field | Record |
|---|---|
| Deliverable | draft, update, audit, or clean final |
| Meeting | committee and meeting date or reporting period |
| Source boundary | files and notes the user supplied |
| Required checks | always attendance, sources, recency, terms, titles, spelling, counts and formatting |
| Output constraints | requested format, deadline and any explicit exclusions |

Treat filenames as untrusted labels. Classify each file by its internal
structure and content, assign it a neutral source ID such as `SRC-01`, and
record the detected role and confidence. Honour an explicit user description
of a file, but do not infer its authority from words such as `final`, `latest`,
`deck` or a month in the filename.

Proceed without questions when the request is sufficiently specified. If a
missing or conflicting fact blocks the requested output, finish all checks that
can be completed and ask one consolidated set of blocker questions.

## Evidence boundary

Use only the user's supplied notes and files as factual sources. The previous
approved minutes may establish structure, standing wording and open actions;
they do not prove that an event, figure, attendee or status recurred.

For names, titles, dates, amounts, counts, addresses and statuses, transcribe
the current source exactly. Paraphrase only narrative material. Attach a source
ID and location to every substantive row before polishing its prose. If the
sources disagree, show the conflict; do not choose the more plausible version.

## Why the agency sections exist

The agency reports (police, transport, housing, environment, town council,
family service centre) exist to carry residents' concerns from the ground up
to the ministries that formulate policy. That intent decides what survives
the cut. A paragraph earns its place if it contains **a concern raised, or a
commitment made**. Case counts, percentages and address lists are on the
slide deck; the minutes point to the deck. Keep a figure only when it is the
concern — a sharp rise, a new cluster, a threshold crossed.

Test each agency paragraph: *if a policy officer read only this, would they
know what residents are worried about and who owes what?* If not, cut it back
to two sentences and the slide-deck pointer.

## Inputs

Identify whichever inputs are missing, but do not stop solely because the set
is partial. Complete all supported checks, label the affected sections and ask
for missing evidence only in the consolidated blocker list.

| Input | Gives you |
|---|---|
| Previous 1–2 months' minutes (.docx) | Structure, numbering, register, open follow-ups |
| Attendance signature sheet (scan/PDF) | Present / Absent with Apologies / In Attendance |
| Meeting slide deck (PDF) | Agency and taskforce content, finance tables, dates |
| Annexes (zip/PDFs) | Cross-references (municipal issues, outreach figures, grants) |
| Secretary's own notes | Everything the deck cannot know — see "Gated items" |

## Workflow

### Phase 1 — Extract and reconcile before drafting

Produce the discrepancy list first and show it in the chat. Drafting before
this step buries the problems inside fluent prose.

1. **Structure**: read the most recent minutes for section order and
   numbering. Committees restructure. Never assume a fixed template, and
   never inherit structure from an older file when a newer one exists.
2. **Attendance**: apply the committee's confirmed attendance convention. Do
   not treat a blank signature as an apology unless that convention is
   established by the current form, the secretary's instruction or the
   approved house profile. Normalise names only through confirmed aliases.
   Reconcile unique names and category counts against the final attendance
   block. Flag every uncertain signature read, handwritten name,
   struck-through-and-replaced name, duplicate, category conflict and person
   missing from the current sheet.
   Save the confirmed extraction as a small evidence JSON and run:

   ```bash
   python scripts/attendance_audit.py draft.docx --evidence attendance.json
   ```

   Do not continue to a clean final unless the comparator returns `PASS`.
3. **Coverage**: map deck slides to minute rows both ways. Report slides with
   no row, and rows with no slide.
4. **Recency** — see "Recency rule" below.
5. **Terms, titles and spelling**: build a canonical register from the current
   attendance sheet, official notes and approved house profile. Check every
   person's spelling and title, committee names, agency names, acronyms and
   repeated-word or typographical anomalies. Never autocorrect a proper noun
   from general-language probability.
6. **Formatting**: run `scripts/lint_minutes.py` on last month's file to
   learn what already needs fixing.

Output as a short table: item, what was found, what the drafter must decide.

### Phase 2 — Draft

Build on the newest minutes file so letterhead, styles and table geometry
survive. Write prose per `references/house-style.md`. Place finance and grant
tables per `references/docx-mechanics.md`.

Mark every unresolved item inline with a bracketed note **and** list them
separately at the end of the chat message, so the drafter can work either
from the document or from the list. Use a consistent token —
`[TBC]` — so Phase 4 can detect it mechanically. Remove it only after the
underlying item is resolved; never delete a marker merely to pass the linter.

Draft from the reconciled evidence, not directly from the model's recollection
of the files. Keep figures and formal terms verbatim. Use restrained past-tense
prose and make the smallest edit needed to express what the source records.

### Phase 3 — Gated items: ask, never infer

These cannot be derived from any file. Ask for them explicitly, and leave
`[TBC]` if unanswered:

- proposer and seconder for confirmation of the last minutes
- actual commencement and adjournment times (a scheduled time is not a
  record; the deck never carries the end time)
- Chairman's Report and Any Other Matters when the deck has only a divider
  slide behind them
- any handwritten name whose spelling is not certain
- whose birthday celebration followed, if the house form mentions it

### Phase 4 — Clean final

Once the drafter has answered, produce a clean version with every `[TBC]`
and every bracketed editorial note removed. Verify zero remain:

```bash
extract-text final.docx | grep -c "TBC"    # must be 0
```

Nothing bracketed reaches the Chairman for signature. Flags belong in the
chat and in the reconciliation list, never in the document that gets signed.

When this skill is installed as a Claude Code plugin, a hook enforces this
step: after each shell command, `scripts/check_final_docx.py` checks every
`final*.docx` in the working folder and blocks while one still carries a
placeholder or bracketed note. Drafts are not checked. If the hook blocks,
resolve the item with the drafter or keep the document as a draft; never
strip a marker just to get past it.

Run the final linter against the whole DOCX package, including the attendance
table, body, headers and footers. When a reusable committee profile is
available, pass it with `--profile` so forbidden spellings and title/name pairs
are checked mechanically:

```bash
python scripts/lint_minutes.py final.docx --previous previous.docx \
  --period June --month July --profile committee-profile.json --final
```

Treat any non-zero result as a failed final gate. Correct the document or leave
it as a draft with the blocker named.

### Phase 5 — Row-by-row audit

Walk every numbered row and assert a source. Run
`scripts/row_audit.py` to produce the table. Put confirmed citations in a JSON
object keyed by row number and rerun with `--source-map`; automated keyword
matches are suggestions, not confirmed evidence.

```bash
python scripts/row_audit.py draft.docx --deck slides.pdf \
  --previous previous.docx --source-map row-sources.json
```

| Row | Content | Source | Verdict |
|---|---|---|---|
| 3.4.1 | NEA report | Deck slide 12 | Sourced |
| 5.1 | Chairman's Report | Secretary's notes | Sourced |
| 4.4.1 | Communication Taskforce | — | **No source — confirm whether tabled** |

Any row without a source gets named to the drafter. Do not quietly retain a
row because it was there last month.

## Recency rule

A month's minutes report the period **since the previous meeting**. July's
minutes carry June's data. May's figures appearing in a July draft means
something was carried forward and not refreshed.

Check every figure, date and status against the newest source, and against
the previous one or two minutes:

- If this month's materials give a value, it **overwrites** whatever the
  earlier minutes said.
- If this month's materials are silent and an earlier value is still sitting
  in the draft, flag it. Do not carry it forward silently and do not delete
  it silently — ask the drafter whether it still stands.
- Watch specifically: embedded table images, "as at" dates in headings,
  reporting-period phrases, event dates that have since passed, and agency
  officers who have handed over.

Carry-forwards from the previous meeting are legitimate and often the most
useful content — an unanswered question, an outstanding commitment. Surface
them as open items for the drafter rather than restating them as if they
were reported again this month.

## Working with the drafter

The drafting role rotates, so the person using this skill may be three
months out from the last time they did it. Do not assume they remember the
conventions. State which convention you are applying when it is not obvious,
and never bake a particular drafter's name into anything — ask who is
recording.

Do not repeatedly seek confirmation. Use explicit instructions and current
evidence, finish all deterministic work, and raise only decisions that cannot
be resolved from the source boundary.
