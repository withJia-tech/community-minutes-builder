# community-minutes-builder


The first version of this skill began with a recurring secretariat problem:
last month's minutes are the easiest document to reuse, but they are also the
easiest place for an old figure, title or status to survive unnoticed.

CCC Minutes Builder adds a checking workflow around that reuse. Given the
previous approved minutes, current attendance sheet, meeting deck and
secretary's notes, it helps produce:

1. a formatted Word draft;
2. a discrepancy report; and
3. a row-by-row source audit.

The current release focuses on a modest standard: do not return `PASS` while a
known attendance, source, recency, terminology or formatting conflict remains.

## How it runs

The skill runs inside the user's supported AI workspace. Meeting records are
provided directly within that user instance, and the draft and audit are
returned there.

It is not a separate website or document portal. The project does not operate
an additional service for uploading meeting records or downloading completed
minutes. This repository holds the skill and its supporting checks.

## Current workflow

```text
Source records
→ extract facts
→ reconcile attendance and reporting periods
→ draft from confirmed evidence
→ run deterministic checks
→ render and inspect
→ PASS / PASS WITH WARNINGS / FAIL
```

The model is used for extraction, restrained summarisation and drafting. The
scripts handle checks that can be made more explicit and repeatable.

### Where each kind of judgement sits

| Layer | Current role |
|---|---|
| Model-assisted | Interpret the request, classify source roles, read meeting material, propose source matches and draft restrained prose. |
| Deterministic scripts | Compare attendance records, enforce approved spellings and titles, detect placeholders and stale artefacts, and fail rows without confirmed sources. |
| Human secretariat | Resolve uncertain handwriting, conflicting evidence, unrecorded discussion and final approval. |

A model-suggested source match is not treated as confirmed evidence. It becomes
confirmed only when it is recorded in the row source map.

## Checks included today

- identify source roles from document contents rather than filenames;
- compare attendance names, titles, categories and counts;
- map each substantive minutes row to a confirmed source;
- flag stale dates, figures, statuses and embedded tables;
- check approved terminology and known name variants;
- detect placeholders, repeated words and structural anomalies; and
- preserve the latest approved Word structure where possible.

Example audit output:

```text
OVERALL VERDICT: FAIL

BLOCKER  Present count is 18 in the evidence but 17 in the minutes
BLOCKER  Row 4.4.1 has no confirmed source
BLOCKER  "Exmaple Name" differs from the approved roster spelling
WARN     An embedded image is unchanged from the previous minutes
```

This output is intended to make review easier. It is not a claim that every
meeting nuance can be resolved automatically.

## Inputs

- previous one or two months' approved minutes (`.docx`);
- current attendance or signature sheet (`.pdf` or scan);
- current meeting slide deck (`.pdf`);
- annexes and supporting records; and
- the secretary's meeting notes.

The skill can work with a partial set. It identifies which checks or sections
cannot be completed from the available evidence.

## Quick start

1. Add the latest approved version of the skill to a supported AI workspace.
2. Invoke it within that user instance.
3. Provide the available meeting records and say whether you want a draft,
   update, audit or clean final.

Example request:

> Prepare the July CCC minutes from these records. Reconcile attendance,
> preserve the approved Word format, check the titles and figures, and show me
> the discrepancies before producing a clean final.

### Run the checks directly

```bash
# Compare the Word attendance table with confirmed current evidence
python scripts/attendance_audit.py draft.docx \
  --evidence attendance.json

# Check placeholders, dates, terms, names, titles and document structure
python scripts/lint_minutes.py draft.docx \
  --previous previous.docx \
  --period June --month July \
  --profile committee-profile.json \
  --final

# Require every numbered row to have a confirmed source
python scripts/row_audit.py draft.docx \
  --deck slides.pdf \
  --previous previous.docx \
  --source-map row-sources.json
```

Each final check returns a non-zero exit status when a blocking condition
remains. This makes the checks usable in a repeatable workflow rather than only
as instructions to the model.

## Model use

The workflow is designed to run on a smaller capable model first. Where the
host provides model controls, it uses low-temperature generation and starts
with a Sonnet-class model. An Opus-class model is considered only when the user
requests it or a complete first pass leaves a named material blocker that the
deterministic checks cannot resolve.

Where those controls are unavailable, the skill continues conservatively
without claiming that a particular model or temperature was selected.

## What still requires judgement

- uncertain handwriting or signatures;
- conflicting current sources;
- discussion or decisions absent from the supplied notes;
- whether an older open item remains active; and
- the final secretariat review and committee approval.

The skill flags these areas instead of filling the gap with plausible prose.

Current technical limitations are also visible:

- attendance extraction expects the established Word attendance-table pattern;
- spelling and title enforcement depends on an approved committee profile;
- keyword-based slide matches are suggestions until a source map confirms them;
- image comparison can detect unchanged embedded files, but not every stale
  table that has been re-exported; and
- scanned signatures and image-heavy slides still require visual review.

## Validation status

The current package has passed structural skill validation and Python syntax
checks. The included controls have also been exercised against small synthetic
cases covering:

- a clean attendance match;
- a wrong attendance category and title;
- an unapproved name spelling;
- unresolved `[TBC]` and `TBD` placeholders;
- a duplicated word; and
- a minute row with no confirmed source.

These tests show that the gates behave as intended on the covered cases. They
do not yet establish reliability across every committee template, scan quality
or Word layout. Broader sanitised fixtures are a sensible next step.

## Repository structure

```text
community-minutes-builder/
├── README.md
├── LICENSE
├── .gitignore
├── SKILL.md
├── references/
│   ├── house-style.md
│   └── docx-mechanics.md
└── scripts/
    ├── attendance_audit.py
    ├── lint_minutes.py
    ├── row_audit.py
    └── swap_slide_images.py
```

The skill itself is the repository root: `SKILL.md`, `references/` and
`scripts/`. When packaging it for an AI workspace, zip those into a folder
named `ccc-minutes-builder`, matching the `name` field in `SKILL.md`.

## Privacy

Do not commit real minutes, attendance sheets, signatures, personal data or
other meeting records to this public repository. Use synthetic or fully
sanitised fixtures for testing.

Users remain responsible for applying their organisation's information-
handling requirements within the AI workspace they choose.

## Contributing

The repository is intended to improve through observed failure cases. A useful
contribution should make one behaviour clearer, more repeatable or easier to
verify.

Fork the project or create a branch, test the change with sanitised material,
and submit it for review. Please preserve four working principles:

- current evidence over inherited text;
- explicit uncertainty over plausible inference;
- deterministic checks before model escalation; and
- one reviewed release for operational use.

Installed skills are snapshots. Users need to add a newer reviewed release to
receive subsequent changes.

## Status

This is an early working release. It is intended to assist a human
secretariat, not replace review, approval or signature. The next improvements
should follow real use: record the failure, make the smallest useful control,
and test it again.
