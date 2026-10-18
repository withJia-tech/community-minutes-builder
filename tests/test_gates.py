"""End-to-end checks of the three gates, run as subprocesses on synthetic files.

Each test asserts the exit code and the exact output line a drafter would see.
"""
import copy

import build
from helpers import FIXTURES, lines, needs_poppler, run_script, write_json

PROFILE = FIXTURES / 'committee-profile.json'
EVIDENCE = FIXTURES / 'attendance.json'
SOURCES = FIXTURES / 'row-sources.json'


def items_with(row, text):
    """Copy of the draft items with one row's text replaced."""
    items = [list(item) for item in build.DRAFT_ITEMS]
    for item in items:
        if item[0] == row:
            item[1] = text
    return [tuple(item) for item in items]


# --- attendance_audit.py -------------------------------------------------------

def test_attendance_clean_passes(docs):
    r = run_script('attendance_audit.py', docs['draft'], '--evidence', EVIDENCE)
    assert r.returncode == 0, r.stdout
    assert 'OVERALL VERDICT: PASS' in lines(r)


def test_attendance_wrong_category_and_title_fails(tmp_path):
    # Evidence: David Ong is Absent with Apologies, title Mr.
    # Minutes: David Ong is listed In Attendance, title Mdm.
    attendance = copy.deepcopy(build.ATTENDANCE)
    attendance[1] = ('Absent with Apologies', [])
    attendance[2] = ('In Attendance', [('Mdm', 'David Ong')])
    draft = build.build_docx(tmp_path / 'draft.docx', attendance=attendance)

    r = run_script('attendance_audit.py', draft, '--evidence', EVIDENCE)
    out = lines(r)
    assert r.returncode == 1
    assert 'OVERALL VERDICT: FAIL' in out
    for blocker in (
            'Absent with Apologies count is 1 in evidence but 0 in minutes',
            'In Attendance count is 0 in evidence but 1 in minutes',
            "'David Ong' is Absent with Apologies in evidence but In Attendance in minutes",
            "'David Ong' has title 'Mr' in evidence but 'Mdm' in minutes"):
        assert 'BLOCKER  ' + blocker in out


# --- lint_minutes.py -----------------------------------------------------------

def test_lint_clean_draft_flags_nothing(docs):
    r = run_script('lint_minutes.py', docs['draft'], '--previous', docs['previous'],
                   '--profile', PROFILE, '--final')
    assert r.returncode == 0, r.stdout
    assert lines(r) == ['OK     nothing flagged']


def test_lint_placeholders_warn_in_draft_and_fail_in_final(tmp_path):
    items = items_with('4', 'Any Other Matters. The meeting ended at [TBC]. '
                            'Date of next meeting TBD.')
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)

    r = run_script('lint_minutes.py', draft, '--profile', PROFILE)
    assert r.returncode == 0, r.stdout
    assert "WARN   document carries 1 placeholder(s) matching '[TBC]'" in lines(r)
    assert "WARN   document carries 1 placeholder(s) matching 'TBD'" in lines(r)

    r = run_script('lint_minutes.py', draft, '--profile', PROFILE, '--final')
    assert r.returncode == 1
    assert "ERROR  document carries 1 placeholder(s) matching '[TBC]'" in lines(r)
    assert "ERROR  document carries 1 placeholder(s) matching 'TBD'" in lines(r)


def test_lint_flags_unapproved_name_alias(tmp_path):
    items = items_with('3', "Chairman's Report. Mdm Alice Lee thanked Mr Benjamin "
                            'Tan and Ms Chloe Ng for organising the lantern walk.')
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)

    r = run_script('lint_minutes.py', draft, '--profile', PROFILE)
    assert ("WARN   unapproved name spelling 'Alice Lee'; canonical name is "
            "'Alice Lim'") in lines(r)


def test_lint_flags_duplicated_word(tmp_path):
    items = items_with('4', 'Any Other Matters. The the meeting ended after '
                            'the announcements.')
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)

    r = run_script('lint_minutes.py', draft)
    assert "WARN   possible duplicated word 'The the'" in lines(r)


# --- row_audit.py --------------------------------------------------------------

def test_row_audit_unmapped_row_blocks(tmp_path, docs):
    sources = write_json(tmp_path / 'sources.json',
                         {'1': 'Secretary\'s notes', '3': 'Secretary\'s notes',
                          '4': 'Secretary\'s notes'})
    r = run_script('row_audit.py', docs['draft'], '--source-map', sources)
    assert r.returncode == 1
    assert 'OVERALL VERDICT: FAIL' in lines(r)
    assert 'BLOCKER  row 2 has no confirmed source' in lines(r)


def test_row_audit_all_rows_mapped_passes(docs):
    r = run_script('row_audit.py', docs['draft'], '--previous', docs['previous'],
                   '--source-map', SOURCES)
    assert r.returncode == 0, r.stdout
    assert 'OVERALL VERDICT: PASS' in lines(r)


def test_row_audit_placeholder_blocks(tmp_path):
    items = items_with('4', 'Any Other Matters. The meeting ended at [TBC].')
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)
    r = run_script('row_audit.py', draft, '--source-map', SOURCES)
    assert r.returncode == 1
    assert 'OVERALL VERDICT: FAIL' in lines(r)
    assert any(line.startswith('BLOCKER  row 4 carries an unresolved')
               for line in lines(r)), r.stdout


@needs_poppler
def test_row_audit_deck_suggests_slide_and_lists_unmatched(tmp_path, docs):
    # Row 2 is deliberately left out of the map, so its source must come
    # from the deck keyword match.
    sources = write_json(tmp_path / 'sources.json',
                         {'1': 'Secretary\'s notes', '3': 'Secretary\'s notes',
                          '4': 'Secretary\'s notes'})
    r = run_script('row_audit.py', docs['draft'], '--deck', docs['deck'],
                   '--source-map', sources)
    out = lines(r)
    assert r.returncode == 0, r.stdout
    row2 = [line for line in out if line.startswith('| 2 |')]
    assert len(row2) == 1 and '| Deck slide 1 |' in row2[0], r.stdout
    assert ('Slides with no matching row — confirm each was either covered '
            'elsewhere or genuinely not tabled: 2') in out
    assert 'OVERALL VERDICT: PASS WITH WARNINGS' in out
    assert 'WARN     row 2 has only an automated source suggestion' in out
