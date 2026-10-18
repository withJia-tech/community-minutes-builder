"""The PostToolUse hook blocks a final that still carries a marker, and nothing else."""
import json

import build
from helpers import run_script

HOOK = 'check_final_docx.py'


def items_with(row, text):
    return [(num, text if num == row else body, action)
            for num, body, action in build.DRAFT_ITEMS]


def run_hook(cwd):
    return run_script(HOOK, stdin=json.dumps({'cwd': str(cwd), 'tool_name': 'Bash'}))


def test_final_with_tbc_blocks(tmp_path):
    build.build_docx(tmp_path / 'final.docx',
                     items=items_with('4', 'The meeting ended at [TBC].'))
    r = run_hook(tmp_path)
    assert r.returncode == 2, r.stderr
    assert 'final.docx' in r.stderr
    assert '[TBC]' in r.stderr


def test_final_in_subfolder_with_mixed_case_name_blocks(tmp_path):
    (tmp_path / 'july').mkdir()
    build.build_docx(tmp_path / 'july' / 'Final_July_Minutes.docx',
                     items=items_with('4', 'Proposed by [name of proposer].'))
    r = run_hook(tmp_path)
    assert r.returncode == 2, r.stderr
    assert '[name of proposer]' in r.stderr


def test_clean_final_passes(tmp_path):
    build.build_docx(tmp_path / 'final.docx')
    r = run_hook(tmp_path)
    assert r.returncode == 0, r.stderr


def test_draft_with_tbc_is_not_checked(tmp_path):
    build.build_docx(tmp_path / 'draft.docx',
                     items=items_with('4', 'The meeting ended at [TBC].'))
    r = run_hook(tmp_path)
    assert r.returncode == 0, r.stderr


def test_final_with_short_citation_passes(tmp_path):
    build.build_docx(tmp_path / 'final.docx',
                     items=items_with('2', 'The NEA officer shared the dengue '
                                           'figures for Block 123 [1].'))
    r = run_hook(tmp_path)
    assert r.returncode == 0, r.stderr


def test_skipped_folders_are_not_searched(tmp_path):
    for folder in ('.git', 'node_modules', 'unpacked'):
        (tmp_path / folder).mkdir()
        build.build_docx(tmp_path / folder / 'final.docx',
                         items=items_with('4', 'The meeting ended at [TBC].'))
    r = run_hook(tmp_path)
    assert r.returncode == 0, r.stderr


def test_non_json_input_fails_open(tmp_path):
    r = run_script(HOOK, stdin='this is not json')
    assert r.returncode == 0
    assert 'skipping' in r.stderr


def test_unreadable_final_fails_open(tmp_path):
    (tmp_path / 'final.docx').write_bytes(b'not a zip file')
    r = run_hook(tmp_path)
    assert r.returncode == 0
    assert 'could not read' in r.stderr
