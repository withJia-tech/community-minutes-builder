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

## Install

### As a Claude Code plugin

```text
/plugin marketplace add withJia-tech/community-minutes-builder
/plugin install ccc-minutes-builder@community-minutes-builder
```

On Claude Code 2.1.275 or later, one line does both:

```text
/plugin install ccc-minutes-builder --marketplace withJia-tech/community-minutes-builder
```

The plugin adds the skill and the final-document hook described below.

### Manual upload (any workspace that accepts a skill zip)

Zip the skill folder itself, so the archive contains a top-level
`ccc-minutes-builder/` folder with `SKILL.md` inside:

```bash
cd skills && zip -r ccc-minutes-builder.zip ccc-minutes-builder -x '*/__pycache__/*'
```

A manual upload gives you the skill but not the hook, so run the Phase 4
checks yourself before calling a document final.

## Quick start

1. Install the plugin, or upload the skill, in a supported AI workspace.
2. Invoke it within that user instance.
3. Provide the available meeting records and say whether you want a draft,
   update, audit or clean final.

Example request:

> Prepare the July CCC minutes from these records. Reconcile attendance,
> preserve the approved Word format, check the titles and figures, and show me
> the discrepancies before producing a clean final.

### Run the checks directly

```bash
cd skills/ccc-minutes-builder

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

## The hook enforces Phase 4

Phase 4 of the skill says nothing bracketed reaches the Chairman for
signature. The plugin turns that rule into a check that runs on its own,
whether or not the model remembers it.

After every shell command Claude runs, a `PostToolUse` hook
(`plugins/ccc-minutes-builder/hooks/hooks.json`) runs
`scripts/check_final_docx.py`. It looks in the working folder for Word files
whose name starts with `final` (`final*.docx`, any case) and reads their
visible text: body, tables, headers, footers, footnotes, endnotes and
comments. If one still carries `[TBC]`, `[time]`, `TBD`, a `[name …]`
placeholder or a bracketed editorial note, the hook exits with code 2 and
Claude Code passes the file name and the markers straight back to Claude.
The hook runs after the command, so it cannot undo the file being written,
but a final that still carries a marker cannot pass unnoticed: Claude has to
resolve the markers with the drafter or leave the document as a draft.

The hook is deliberately narrow:

- **Only finals.** Drafts carry `[TBC]` legitimately until Phase 4, so a file
  named `draft.docx` is never checked.
- **Only known markers.** It uses the same patterns as `lint_minutes.py`. A
  short bracket such as the citation `[1]` does not count.
- **Fails open.** Unreadable input, a missing `lxml` or a damaged file prints
  a note and lets work continue. The hook guards the signature step; it is
  not a replacement for running the linter with `--final`.

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

The test suite in `tests/` generates small synthetic Word and PDF files and
runs each script the way a user would, checking exit codes and exact output
lines. CI is set up to run it on Python 3.10–3.12 for every pull request and
every push to `main`. The tests show that:

- the attendance audit passes a clean match and blocks a wrong category or
  title, naming the person;
- the linter passes a clean draft and flags placeholders (a warning in draft
  mode, an error with `--final`), unapproved name spellings and duplicated
  words;
- the row audit blocks a row with no confirmed source or with an unresolved
  marker, suggests a deck slide for a matching row and lists slides that no
  row covers;
- the hook blocks a `final*.docx` that still carries a marker, and leaves
  drafts, citations such as `[1]` and unreadable input alone;
- the plugin's manifests, skill paths and hook paths resolve, and no symlink
  loops back into the plugin; and
- the four failures in [`research/failures.md`](research/failures.md) stay
  fixed, each pinned by a regression test and a true-positive test.

The marketplace manifest also passes `claude plugin validate . --strict`,
checked locally rather than in CI.

These are small invented cases in the established table layout. They do not
establish reliability across every committee template, scan quality or Word
layout, and they say nothing about the quality of model-drafted prose. Every
entry in the failures log so far comes from synthetic stress tests, not real
meetings.

## Repository structure

```text
community-minutes-builder/
├── README.md
├── LICENSE
├── requirements-dev.txt          # lxml, pytest
├── .claude-plugin/
│   └── marketplace.json          # lists the plugin below
├── .github/workflows/ci.yml      # py_compile + pytest on Python 3.10–3.12
├── skills/
│   └── ccc-minutes-builder/      # the skill itself
│       ├── SKILL.md
│       ├── references/
│       │   ├── house-style.md
│       │   └── docx-mechanics.md
│       └── scripts/
│           ├── attendance_audit.py
│           ├── check_final_docx.py   # the Phase 4 hook
│           ├── lint_minutes.py
│           ├── row_audit.py
│           └── swap_slide_images.py
├── plugins/
│   └── ccc-minutes-builder/
│       ├── .claude-plugin/plugin.json
│       ├── hooks/hooks.json
│       └── skills/ccc-minutes-builder -> ../../../skills/ccc-minutes-builder
├── research/
│   └── failures.md               # observed failures, fixes and their tests
└── tests/
    ├── fixtures/                 # synthetic JSON + build.py (no binaries)
    ├── test_gates.py
    ├── test_hook.py
    └── test_structure.py
```

The skill lives in `skills/ccc-minutes-builder/`. Paths inside `SKILL.md`,
such as `scripts/lint_minutes.py`, are relative to that folder. The plugin
reaches the skill through a symlink to that folder (never to the repository
root, which would make the plugin contain itself); Claude Code copies the
real files when it installs the plugin. For a manual upload, zip the skill
folder; its name matches the `name` field in `SKILL.md`.

## Running the tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

The deck tests need Poppler (`pdfinfo`, `pdftotext`) and are skipped when it
is not installed. The `.docx` and `.pdf` fixtures are generated into a
temporary folder at test time by `tests/fixtures/build.py`, so the
repository's rule against committing Word and PDF files stays intact.

## Privacy

Do not commit real minutes, attendance sheets, signatures, personal data or
other meeting records to this public repository. Use synthetic or fully
sanitised fixtures for testing.

Users remain responsible for applying their organisation's information-
handling requirements within the AI workspace they choose.

## Contributing

The repository is intended to improve through observed failure cases. A useful
contribution should make one behaviour clearer, more repeatable or easier to
verify. Record each failure in [`research/failures.md`](research/failures.md)
following its protocol: symptom, root cause, smallest fix, and a regression
test plus a true-positive test that pin it.

Fork the project or create a branch, test the change with synthetic or
sanitised material, run `python -m pytest tests/`, and submit it for
review. Please preserve four working principles:

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
