# Transcripts and recordings

Read this only when the drafter supplies a meeting transcript. A transcript
adds evidence of what was said. It never adds evidence of what was decided,
and in a large hall it misses whatever no microphone heard.

## Before using one

Ask, if the drafter has not said: **was the recording announced and agreed
before it started?** If not, do not use it; draft from the notes and markers
alone. Recordings and transcripts stay in the drafter's private `workspace/`
folder, never in a repository, and are deleted under the committee's rules.

## The secretary's markers decide what goes in

The secretary keeps time-stamped markers during the meeting, one per line:

```text
19:52 Agency update: cluster rise; hit-rate question owed an answer
```

Run:

```bash
python scripts/transcript_windows.py --transcript meeting.vtt \
  --markers markers.txt --recording-start 19:30
```

- Only the transcript text inside a marker's window may feed the draft.
- **Unmarked stretches** are listed as suggestions. Put them in the
  discrepancy list as "possible items, drafter decides". Never turn one into
  a minutes row without the drafter's confirmation.
- A `FAIL` blocks drafting from the transcript. Fix the markers or the start
  time, or draft that item from the notes alone.

Formats: `.vtt`, `.srt`, or `.txt` lines like `[00:41:12] Speaker: text`.
Convert a `.docx` transcript before use. Markers may also be offsets from the
start of the recording, written `+41:12`.

## What a transcript can and cannot support

| Transcript shows | Still needs |
|---|---|
| That something was said, roughly when | A marker or note to put it in the minutes |
| A question asked or a concern raised | Nothing more, once marked, if the wording is clear |
| A decision, resolution, agreement or commitment | The secretary's marker or note, or the drafter's confirmation |
| A speaker label | A match against the attendance sheet or committee profile |
| A name as heard | The attendance sheet's spelling, never the transcript's |

- **A meeting tool's AI recap or summary is not a source.** It is another
  model's reading of the meeting. Use only the transcript text.
- **Gaps are never reconstructed.** `[inaudible]`, crosstalk or no coverage
  around a marker means the item gets `[TBC]` unless the notes cover it.
- **Mixed-language or colloquial passages** are often transcribed wrongly.
  Treat them as needing the drafter's reading before use.
- **Minutes are not a transcript.** Paraphrase in restrained past tense and
  keep the house-style test: a concern raised, or a commitment made. Quote
  only where the exact words matter.

## Citing a transcript

In `row-sources.json`, cite the window and its marker:

```json
{"3.4.1": "Transcript 0:21:10–0:22:45 (marker 19:52)"}
```

`row_audit.py` treats this like any other confirmed citation, so only the
drafter should enter it.
