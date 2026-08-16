# ccc-minutes-builder

A Claude skill for drafting and quality-checking Citizens' Consultative
Committee (CCC) monthly meeting minutes — built for a secretariat where the
drafting duty rotates, so no one person carries the house conventions in
their head.

## What it does

Given the previous month's minutes, a scanned attendance sheet, the meeting
slide deck, and any annexes, it:

1. Reconciles the four inputs against each other **before** drafting anything
   — attendance signatures (`scripts/attendance_audit.py` against a confirmed
   evidence ledger), deck-to-agenda coverage, and whether figures are this
   month's or a stale carry-forward.
2. Drafts the minutes on top of the previous file (preserving letterhead,
   styles, table geometry), using a house register: name presenters as the
   attendance sheet has them, state agency handovers explicitly, and keep
   agency paragraphs to a concern-and-a-commitment rather than restating the
   deck's counts.
3. Leaves anything it cannot know — proposer/seconder, adjournment time,
   Chairman's Report when the deck has only a divider slide — as an explicit
   `[TBC]`, listed separately for the drafter, never silently invented.
4. Produces a clean final with every placeholder stripped, and only after
   the deterministic checks in `scripts/lint_minutes.py` pass.
5. Runs a row-by-row audit that traces every numbered item to a source —
   split into a cheap text-matching triage pass and a slower, required
   visual-verification pass, because a chunk of the deck is screenshots of
   tables that a keyword matcher literally cannot see.

## Why it's shaped this way

The failure mode that matters for a signed record is not a slow draft — it's
a fluent one that asserts something nobody said, or carries last month's
number forward under this month's date. Every design choice here is meant
to surface that kind of error to the drafter before it reaches the
Chairman's signature, not to produce a faster-looking paragraph.

See `SKILL.md` for the full workflow, `references/house-style.md` for the
register and phrasing rules, and `references/docx-mechanics.md` for the
.docx surgery.

## Using it

1. Install as a Claude skill (claude.ai: Settings → Features → upload this
   folder as a zip; Team/Enterprise: an org owner can provision it centrally
   via Organization settings → Skills).
2. In a fresh conversation, attach: last month's minutes (.docx), the
   attendance sheet (PDF/image), the slide deck (PDF), and any annexes.
3. Ask for the minutes to be drafted, or ask for a check against an existing
   draft. The skill will ask for whatever it's missing.

## Adapting it for another committee

The house-style and structural assumptions (three-cell item table, a
PRESENT/ABSENT/IN ATTENDANCE roster block, the concern-and-commitment rule
for agency paragraphs) come from one committee's actual documents. Fork it,
replace `references/house-style.md` with your own committee's conventions,
and adjust the table-shape assumptions in `scripts/*.py` if your minutes
format differs. Pull requests that generalise the scripts (rather than
hard-coding one house's layout) are especially welcome.

## Status

Built and lightly tested against one committee's April, June, and July 2026
minutes. Not yet run against a second committee's format — expect to find
and fix assumptions that turn out to be house-specific rather than general.

## License

MIT — see LICENSE.
