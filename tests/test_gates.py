"""End-to-end checks of the three gates, run as subprocesses on synthetic files.

Each test asserts the exit code and the exact output line a drafter would see.
"""
import copy

import build
from helpers import FIXTURES, SKILL as SKILL_DIR, lines, needs_poppler, run_script, write_json

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
    assert r.returncode == 1, r.stdout
    row2 = [line for line in out if line.startswith('| 2 |')]
    assert len(row2) == 1 and '| Deck slide 1 |' in row2[0], r.stdout
    assert ('Slides with no matching row — confirm each was either covered '
            'elsewhere or genuinely not tabled: 2') in out
    assert 'OVERALL VERDICT: FAIL' in out
    assert 'BLOCKER  row 2 has no confirmed source' in out


# --- regression tests: research/failures.md --------------------------------------
# Each failure gets a regression test (the bug stays fixed) and a true-positive
# test (the fix did not switch the check off).

ADVISER = 'Grassroots Adviser (present today)'


def adviser_evidence(tmp_path, category='Absent with Apologies'):
    data = {'Present': [{'name': n, 'title': t} for t, n in build.ATTENDANCE[0][1]],
            'Absent with Apologies': [], 'In Attendance': []}
    data[category].append({'name': 'David Ong', 'title': ADVISER})
    return write_json(tmp_path / 'attendance.json', data)


def test_failure_1_title_containing_category_word_is_not_a_header(tmp_path):
    attendance = copy.deepcopy(build.ATTENDANCE)
    attendance[1] = ('Absent with Apologies', [(ADVISER, 'David Ong')])
    draft = build.build_docx(tmp_path / 'draft.docx', attendance=attendance)

    r = run_script('attendance_audit.py', draft, '--evidence', adviser_evidence(tmp_path))
    assert r.returncode == 0, r.stdout
    assert 'OVERALL VERDICT: PASS' in lines(r)


def test_failure_1_true_positive_category_conflict_still_reported(tmp_path):
    # Minutes list the adviser as Present; evidence says Absent with Apologies.
    attendance = copy.deepcopy(build.ATTENDANCE)
    attendance[0] = ('Present', attendance[0][1] + [(ADVISER, 'David Ong')])
    attendance[1] = ('Absent with Apologies', [])
    draft = build.build_docx(tmp_path / 'draft.docx', attendance=attendance)

    r = run_script('attendance_audit.py', draft, '--evidence', adviser_evidence(tmp_path))
    out = lines(r)
    assert r.returncode == 1
    assert ("BLOCKER  'David Ong' is Absent with Apologies in evidence but "
            "Present in minutes") in out
    assert "BLOCKER  'David Ong' is in evidence but missing from minutes" not in out


def nea_profile(tmp_path):
    return write_json(tmp_path / 'profile.json',
                      {'term_replacements': {'NEA': 'National Environment Agency'}})


NEA_WARNING = ("WARN   unapproved term or spelling 'NEA'; approved form is "
               "'National Environment Agency'")


def test_failure_2_term_rule_does_not_fire_inside_a_word(tmp_path):
    items = [('1', 'Environment. Residents near Block 123 asked for more '
                   'frequent checks of stagnant water.', '')]
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)

    r = run_script('lint_minutes.py', draft, '--profile', nea_profile(tmp_path))
    assert NEA_WARNING not in lines(r), r.stdout


def test_failure_2_true_positive_standalone_term_still_warns(tmp_path):
    items = [('1', 'Environment. The NEA officer shared the dengue update.', 'NEA')]
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)

    r = run_script('lint_minutes.py', draft, '--profile', nea_profile(tmp_path))
    assert NEA_WARNING in lines(r), r.stdout


def test_failure_3_short_citation_passes_row_audit(tmp_path):
    items = items_with('2', 'Environment. The NEA officer shared that dengue '
                            'cases around Block 123 had fallen [1].')
    draft = build.build_docx(tmp_path / 'draft.docx', items=items)

    lint = run_script('lint_minutes.py', draft, '--final')
    assert lint.returncode == 0, lint.stdout
    r = run_script('row_audit.py', draft, '--source-map', SOURCES)
    assert r.returncode == 0, r.stdout
    assert 'OVERALL VERDICT: PASS' in lines(r)


def test_failure_3_true_positive_markers_still_block_row_audit(tmp_path):
    for marker in ('[TBC]', '[check figures with the NEA officer]'):
        items = items_with('2', 'Environment. The NEA officer shared that '
                                'dengue cases had fallen %s.' % marker)
        draft = build.build_docx(tmp_path / 'draft.docx', items=items)
        r = run_script('row_audit.py', draft, '--source-map', SOURCES)
        assert r.returncode == 1, (marker, r.stdout)
        assert any(line.startswith('BLOCKER  row 2 carries an unresolved')
                   and marker in line for line in lines(r)), (marker, r.stdout)


# --- action tags come from the profile, not from the code ------------------------

CARRIED_OVER = [('1', 'Transport. Residents asked for a bus stop shelter.', 'LTA')]
LTA_WARNING = ('WARN   row 1 action column is tagged LTA but the row does not '
               'mention LTA — likely carried over')


def test_action_tags_default_to_none(tmp_path):
    # No profile, so no agency list is assumed: a fork outside Singapore
    # must not get warnings about someone else's agencies.
    draft = build.build_docx(tmp_path / 'draft.docx', items=CARRIED_OVER)
    r = run_script('lint_minutes.py', draft)
    assert LTA_WARNING not in lines(r), r.stdout


def test_action_tags_from_profile_still_warn(tmp_path):
    draft = build.build_docx(tmp_path / 'draft.docx', items=CARRIED_OVER)
    profile = write_json(tmp_path / 'profile.json', {'action_tags': ['LTA', 'HDB']})
    r = run_script('lint_minutes.py', draft, '--profile', profile)
    assert LTA_WARNING in lines(r), r.stdout


def test_example_profile_runs_through_the_linter(docs):
    example = SKILL_DIR / 'examples' / 'committee-profile.example.json'
    r = run_script('lint_minutes.py', docs['draft'], '--profile', example)
    assert r.returncode == 0, r.stdout
