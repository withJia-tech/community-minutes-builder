# Volunteer guide: writing the minutes with your own AI

The minutes rotate between volunteers, and each of us uses our own AI
account. This guide keeps the result the same whoever writes it: the same
skill, the same committee profile, the same request, the same checks.

The skill drafts and checks. It does not approve. A script `PASS` is not the
committee's approval; the chair and the committee still decide.

## 1. Set up once

Pick the row that matches your account.

| You use | Do this | You get |
|---|---|---|
| **Claude Code** | `/plugin marketplace add withJia-tech/community-minutes-builder` then `/plugin install ccc-minutes-builder@community-minutes-builder` | The skill, plus a hook that blocks a `final*.docx` that still has `[TBC]` in it |
| **Claude (app or web) with skills** | Download the repository, zip the `skills/ccc-minutes-builder` folder, and upload the ZIP where your Claude settings manage skills | The skill, without the hook |
| **Grok, ChatGPT, Qwen or another assistant** | Attach `portable/minutes-instructions.md` at the start of each chat. Follow `portable/README.md` | The same rules, generated from the Claude skill. The assistant hands back draft text and two JSON files for the checker |

Claude users: ask the AI to run `scripts/preflight.py`. If it says `FAIL`, the
checks cannot run in that workspace: you can still draft, but do not call
anything a checked final.

Everyone else: the committee's checker (one volunteer with Python, until the
browser checker is ready) runs the checks on your Word file and the two JSON
files. See "Run the checks directly" in the README.

## 2. Use the shared committee profile

One person keeps the committee profile, a small file of approved names,
titles and terms (start from
`skills/ccc-minutes-builder/examples/committee-profile.example.json`).

- It contains real names, so share it **privately** (the committee's own
  drive), never in a public repository.
- Everyone uses the latest copy, and the checks use it with `--profile`.
- When a name or title changes, tell the keeper; don't fix it in your copy.

## 3. Before and during the meeting

- Collect: last month's approved minutes, this month's attendance sheet, the
  slide deck, any annexes.
- Keep short notes. If anything is recorded, also keep **time-stamped
  markers**, one per line, for each moment that belongs in the minutes:

  ```text
  19:52 Agency update: cluster rise; hit-rate question owed an answer
  ```

- **Recording?** Announce it and get agreement first, for example: *"This
  meeting is being recorded only to help prepare the minutes. The recording
  will be deleted once the minutes are approved. Please tell the chair now if
  you object."* If anyone objects, don't record.

## 4. After the meeting

1. Put everything in a private folder called `workspace/` on your own
   computer. Never put meeting files in this repository.
2. Paste the **standard request**, filling in the brackets:

   > Use the ccc-minutes-builder skill. Prepare the [month] minutes for
   > [committee] from the attached records: previous minutes, attendance
   > sheet, slide deck and my notes [and the transcript with my markers; the
   > recording started at HH:MM]. Use the committee profile. Show me the
   > discrepancy list and the questions only I can answer first. Do not add
   > anything that is not in these records. Mark anything unresolved
   > [TBC]. Produce a clean final only after I have answered and every
   > check passes.

3. Answer the questions it asks: proposer and seconder, start and end times,
   uncertain handwriting, anything heard only on a recording.
4. Read the verdicts:
   - **FAIL**: something is missing or wrong. Fix it from the real records.
     Never delete a `[TBC]` or a row just to make a check pass.
   - **PASS WITH WARNINGS**: read each warning and decide.
   - **PASS**: the checks found nothing. It is ready for the chair's review,
     not approved.

A transcript only helps through your markers: the AI may use what was said
around each marker, and lists everything else as suggestions for you to
decide. Rules: `references/transcripts.md`, script:
`scripts/transcript_windows.py`.

## 5. Your account's data settings

Meeting records go to whichever AI provider you upload them to, under your
own account's settings. Check your account's data, training and history
settings before uploading. Don't upload recordings to an account you don't
control, and delete recordings and transcripts when the committee's rules
say so.

## 6. Stay on the same version

Before each meeting, check you have the latest release.

- **Claude Code:** run `/plugin marketplace update`, then update the plugin
  if a new version is offered.
- **ZIP upload:** download the latest release and upload the new ZIP.
- **Other assistants:** download the latest `portable/minutes-instructions.md`
  and check the version line at its top matches the Claude plugin's.

If two secretaries get different results from the same records, compare
versions first.
