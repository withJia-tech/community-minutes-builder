# Observed failures

This log records each failure the checks have shown, why it happened, the
smallest fix and the test that keeps it fixed. It exists so that every
control in this repository can be traced to a failure someone saw.

**Entries 1–4 came from synthetic stress tests during development, not from
real meetings.** Entries 1–3 were reproduced against the real scripts with
invented fixtures (`tests/fixtures/`). Entry 4 was found on review of the
packaged plugin folder. No real minutes, attendance sheets or personal data
were used.

## Protocol for new entries

Later entries should come from real, anonymised use. For each one:

1. **Symptom.** Describe what the drafter saw: the wrong verdict, the missing
   flag, the misleading message. Use no names, dates or meeting content.
2. **Reproduce.** Build the smallest synthetic case that shows it, using
   `tests/fixtures/build.py`. Confirm the new test fails before you fix
   anything.
3. **Root cause.** Name the line or rule that produced the failure.
4. **Smallest fix.** Change only what the failure needs.
5. **Pin it.** Add a regression test (the failure stays fixed) and a
   true-positive test (the check still catches what it is meant to catch).
6. **Record it here** with the same four headings.

---

## 1. A title containing a category word was read as a header

`skills/ccc-minutes-builder/scripts/attendance_audit.py`

- **Symptom.** A person with the title "Grassroots Adviser (present today)"
  disappeared from the attendance audit. The blocker said they were "in
  evidence but missing from minutes", although their row was in the table.
  The category count was also wrong, and anyone listed after that row, up to
  the next heading, was counted as Present.
- **Root cause.** Every row was searched for a category word. The word
  "present" in the title matched the `Present` heading, so the person row
  was treated as a header: the person was dropped and the current category
  switched to Present.
- **Smallest fix.** Only a row with fewer than 4 cells is checked for a
  category word. Header rows are short; person rows have 4 cells
  (`[n, title, '', name]`).
- **Pinned by.** `tests/test_gates.py`:
  `test_failure_1_title_containing_category_word_is_not_a_header`
  (regression) and
  `test_failure_1_true_positive_category_conflict_still_reported`
  (true positive: the same person in the wrong section is reported as a
  category conflict, not as missing).

## 2. A term rule fired inside another word

`skills/ccc-minutes-builder/scripts/lint_minutes.py`, `term_replacements`

- **Symptom.** A profile rule for `NEA` (approved form "National Environment
  Agency") warned on a draft whose only match was the word "near".
- **Root cause.** Term rules used an unbounded substring search, while the
  alias check in the same file already matched whole terms only.
- **Smallest fix.** Use the alias check's boundary, `(?<!\w)%s(?!\w)`, for
  term rules too.
- **Pinned by.** `tests/test_gates.py`:
  `test_failure_2_term_rule_does_not_fire_inside_a_word` (regression) and
  `test_failure_2_true_positive_standalone_term_still_warns` (true positive:
  a standalone `NEA` still warns).

## 3. The row audit and the linter disagreed about brackets

`skills/ccc-minutes-builder/scripts/row_audit.py` and `lint_minutes.py`

- **Symptom.** A row citing its source as `[1]` passed
  `lint_minutes.py --final` but failed `row_audit.py` with "row 2 carries an
  unresolved bracket". Two gates gave opposite verdicts on the same text.
- **Root cause.** `row_audit.py` flagged any `[`. The linter flags only its
  placeholder patterns (`[TBC]`, `[time]`, `[name …]`, `TBD` and others) and
  bracketed notes of four or more characters, so short citations pass.
- **Smallest fix.** Add `unresolved_markers(text)` to `lint_minutes.py`,
  built from the linter's own `PLACEHOLDERS` and bracketed-note rule. Call
  it from `row_audit.py` and from the final-document hook. The linter's own
  output is unchanged. The row-audit message now names the markers ("row 2
  carries an unresolved marker: [TBC]"), because the shared rule also covers
  `TBD`, which has no bracket.
- **Pinned by.** `tests/test_gates.py`:
  `test_failure_3_short_citation_passes_row_audit` (regression),
  `test_failure_3_true_positive_markers_still_block_row_audit` and
  `test_row_audit_placeholder_blocks` (true positives: `[TBC]` and a
  bracketed note still block). `tests/test_hook.py`:
  `test_final_with_short_citation_passes`.

## 4. The plugin folder contained itself

`plugins/ccc-minutes-builder/skills/`

- **Symptom.** In an earlier, unpublished version, the plugin reached the
  skill through a symlink to the repository root. The root contains
  `plugins/`, so the plugin folder contained itself: paths such as
  `plugins/…/skills/ccc-minutes-builder/plugins/…/skills/…` never ended, and
  `find -L` reported "File system loop detected". Any tool that copies or
  packages by following symlinks would loop or fail.
- **Root cause.** The skill lived at the repository root, so the only folder
  that held `SKILL.md` was the root itself.
- **Smallest fix.** Move the skill to `skills/ccc-minutes-builder/` and point
  the link there:
  `plugins/ccc-minutes-builder/skills/ccc-minutes-builder -> ../../../skills/ccc-minutes-builder`.
  Installing the plugin locally with `claude plugin install` was checked to
  copy the real skill files into the plugin cache.
- **Pinned by.** `tests/test_structure.py`:
  `test_no_symlink_under_plugins_loops_into_an_ancestor` (regression: it
  fails when the link is pointed back at the root) and
  `test_plugin_skill_paths_resolve_to_skill_folders` (true positive: the
  link still reaches a folder with `SKILL.md`).
