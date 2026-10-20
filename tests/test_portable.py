"""The generic instructions are generated from the skill and match the real checks."""
import importlib.util
import json
import re
import subprocess
import sys

import pytest

from helpers import REPO, SCRIPTS

TOOL = REPO / 'tools' / 'build_portable.py'
PORTABLE = REPO / 'portable' / 'minutes-instructions.md'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module('build_portable', TOOL)


def portable_text():
    return PORTABLE.read_text(encoding='utf-8')


def json_block_after(text, heading):
    """The first ```json block after a line containing `heading`."""
    start = text.index(heading)
    m = re.search(r'```json\n(.*?)\n\s*```', text[start:], re.S)
    assert m, 'no json example after %r' % heading
    return json.loads(m.group(1))


def test_generated_file_is_up_to_date():
    result = subprocess.run([sys.executable, str(TOOL), '--check'],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('term', ['Sonnet', 'Opus', 'Claude Code', 'plugin', 'hook',
                                  'CLAUDE_PLUGIN_ROOT'])
def test_no_claude_only_wording_reaches_the_generic_version(term):
    assert term.lower() not in portable_text().lower()


def test_claude_skill_keeps_its_claude_only_parts():
    skill = (REPO / 'skills' / 'ccc-minutes-builder' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'Sonnet-class' in skill and 'Claude Code plugin' in skill


def test_includes_house_style_and_transcripts_but_not_docx_mechanics():
    text = portable_text()
    assert '# House style' in text
    assert '# Transcripts and recordings' in text
    assert '# Working on the .docx' not in text


def test_version_line_matches_plugin_json():
    plugin = json.loads((REPO / 'plugins' / 'ccc-minutes-builder' / '.claude-plugin' /
                         'plugin.json').read_text(encoding='utf-8'))
    assert 'version %s.' % plugin['version'] in portable_text()


def test_attendance_example_parses_with_the_real_checker(tmp_path):
    example = json_block_after(portable_text(), '**attendance.json**')
    path = tmp_path / 'attendance.json'
    path.write_text(json.dumps(example), encoding='utf-8')
    attendance_audit = load_module('attendance_audit', SCRIPTS / 'attendance_audit.py')
    people = attendance_audit.evidence_rows(str(path))
    assert {p['category'] for p in people} == {'Present', 'Absent with Apologies', 'In Attendance'}


def test_row_sources_example_has_the_shape_row_audit_reads():
    example = json_block_after(portable_text(), '**row-sources.json**')
    assert isinstance(example, dict) and example
    for row, citation in example.items():
        assert re.fullmatch(r'\d+(\.\d+)*', row), row
        assert isinstance(citation, str) and citation.strip()


@pytest.mark.parametrize('text, problem', [
    ('a\n<!-- claude-only -->\nb\n', 'never closed'),
    ('a\n<!-- /claude-only -->\n', 'closed without opening'),
    ('<!-- claude-only -->\n<!-- claude-only -->\n<!-- /claude-only -->\n', 'opened twice'),
])
def test_unbalanced_markers_stop_the_build(text, problem):
    with pytest.raises(builder.MarkerError, match=problem):
        builder.strip_claude_only(text)


def test_marked_blocks_are_removed():
    text = 'keep\n<!-- claude-only -->\ndrop\n<!-- /claude-only -->\nkeep too\n'
    assert builder.strip_claude_only(text) == 'keep\nkeep too\n'
