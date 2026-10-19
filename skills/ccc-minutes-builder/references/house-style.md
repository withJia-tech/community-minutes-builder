# House style

## Naming

- **Presenters are named as recorded on the attendance sheet**, not as the
  previous minutes named them. Officers rotate; the sheet is the record of
  who was in the room. Where a name is struck through and replaced by hand,
  the replacement is the presenter.
- **State handovers explicitly** when an agency changes representative:
  *"Mr X formally took over from Mr Y as the Town Council representative to
  the constituency."* This matters to members who will deal with them.
- **One representative present is sufficient.** If an agency's report was
  tabled, write *"Mr X shared…"* plainly. Never append a note about who did
  or did not sign the sheet — that is the drafter's private reconciliation
  problem, not part of the record.
- **Appointment before name** on first mention in a sentence where the
  appointment carries weight: *"Assistant Secretary, Mr A B, proposed…"*,
  *"Adviser, Mr C D, asked…"*.
- **Political office holders** are written by their committee role, not their
  ministerial title. Raw notes may abbreviate ("MOS"); the minutes say
  *"Adviser, Mr [full name]"*.
- Do not carry honorific guesses. If a handwritten name's title or spelling
  is uncertain, ask.

### Canonical name and title register

Before drafting, create one working register from the current attendance
sheet, official notes and any approved committee profile. Record each person's
canonical name, allowed title or committee role, confirmed aliases and the
source location. Current official evidence overrides an older roster. A
previous-minute spelling is not authority when the current record differs.

Check the completed document in both directions:

- every name in the attendance block appears once in the correct category;
- every person named in the body uses a canonical spelling;
- the first substantive mention uses an approved title or committee role;
- no title is upgraded, translated or inferred from general knowledge; and
- an apparent misspelling of a proper noun is flagged, never silently fixed.

When using `scripts/lint_minutes.py --profile`, supply a JSON profile such as:

```json
{
  "term_replacements": {
    "Citizens Consultative Committee": "Citizens' Consultative Committee"
  },
  "people": [
    {
      "name": "Example Name",
      "titles": ["Assistant Secretary"],
      "aliases": ["Exmaple Name"]
    }
  ],
  "action_tags": ["AGENCY-A", "AGENCY-B"]
}
```

`action_tags` lists the agency or office tags that appear in the action
column. When a row's action column carries a tag that the row text never
mentions, the linter warns that it was probably carried over from last month.
There is no built-in list, because agencies differ by committee: leave the key
out and the check is off. A ready-to-copy file is in
`examples/committee-profile.example.json`.

Replace the example values with approved evidence. Treat aliases as spellings
that must not appear in the final document, not as permission to rewrite a
name without review.

## Who appears in the attendance block

Committee members and the constituency office and agency representatives.
Members of *other* committees who signed the sheet as guests do not belong
in the roster — In Attendance stops at agency and office representatives.
They may still be named in the body where the Chairman thanked them.

## Agency paragraphs

Two sentences is the working target. Structure:

1. Who presented and what they covered.
2. The concern, the commitment, or the follow-up owed.

Then the standing pointer: *"Please refer to the [agency] slide deck for
more information."*

Use bullets instead of a second sentence when a single report generated
several distinct follow-ups — a reader scanning for what their committee
owes should not have to parse a paragraph.

**Example — too much**

> Ms F from NEA shared the following update: (1) Dengue Situation Report —
> from 1 January to 9 July, Singapore recorded 1,380 cases, the district 223
> cases, and the constituency 21 cases (8 new). Cases were recorded at [six
> addresses]. (2) Common Breeding Habitats — 8 detected, at [three
> addresses]. (3) High-Rise Littering — [five surveillance periods listed]…

**Example — right**

> Ms F from NEA highlighted that the constituency recorded 21 dengue cases
> from 1 January to 9 July, of which 8 are new, with one active cluster at
> [road], and cautioned that the peak dengue period is approaching. She also
> reported a high-rise littering act captured at [block] which is under
> investigation; Adviser, Mr Z, asked for the hit rates for the spots that
> have been identified, and NEA will respond.

The second keeps the rising trend, the cluster, the seasonal warning, the
enforcement result, and the question a Minister asked that is still owed an
answer. The addresses and sub-counts are on the slide.

## Tone

- Past tense, third person, no adjectives of approval.
- Report what was said, not whether it was good. *"Chairman noted that the
  tour was well put together, and thanked the volunteers"* records the
  Chairman's assessment; it does not offer the secretariat's.
- Resolve pronouns to names where a reader outside the meeting would guess.
- Expand an acronym on first use in the document, then use it freely.
- Keep the standing boilerplate items (conflict-of-interest reminders,
  annex pointers) verbatim from the previous minutes. They are not
  drafting opportunities.

## Numbers and dates

- Dates in full: *8 August 2026*, not *8/8/26*.
- Money with the currency symbol and two decimals where the source has them.
- Where a figure is approximate in the source, say so: *"some 1,000 pieces
  of feedback"*.

## The closing item

The final numbered item records the adjournment and the next meeting. Check
three things every time, because all three drift:

1. The **adjournment time** — comes from the drafter, never the deck.
2. The **next meeting date** — usually the same weekday-of-month pattern,
   but confirm against the deck's closing slide.
3. The **venue** — do not assume it repeats. A venue change is easy to miss
   and embarrassing to get wrong.
