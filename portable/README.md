# Generic version: any AI assistant

For secretaries using Grok, ChatGPT, Qwen or any other chat assistant. Claude
users should install the skill instead (see the main README); it can run the
checks itself.

`minutes-instructions.md` holds the same rules as the Claude skill, with the
Claude-only parts removed and a short section on top for chat assistants. It
is generated from `skills/ccc-minutes-builder`, so both versions always say
the same thing. Do not edit it by hand.

## How to use it

1. Start a new chat and attach `minutes-instructions.md`. If your assistant
   has a place for saved instructions or project files that accepts a file
   this long, you can keep it there instead of attaching it each time.
2. Attach the meeting records and paste the **standard request** from the
   [volunteer guide](../docs/volunteer-guide.md).
3. Answer its questions. It gives back a discrepancy table, draft text,
   `attendance.json` and `row-sources.json`.
4. Paste the draft text into last month's Word file and save it as this
   month's draft.
5. Send the Word file and both JSON files to the committee's checker. Only
   the checker's scripts can say `PASS` or `FAIL`; the assistant is told never
   to.

Check the version line at the top of `minutes-instructions.md` before each
meeting. It matches the Claude plugin's version, so everyone can confirm they
are on the same rules.

## Coming later

A browser checker that runs the same checks on your own computer, with no
installation and no upload, so any secretary can check their own file. Until
then, one volunteer with Python runs the checks for everyone (see "Run the
checks directly" in the main README).
