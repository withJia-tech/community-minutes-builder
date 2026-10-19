"""transcript_windows.py: markers decide what a transcript may feed, and it fails closed."""
import pytest

from helpers import FIXTURES, run_script

SCRIPT = 'transcript_windows.py'
VTT = FIXTURES / 'transcript.vtt'
TXT = FIXTURES / 'transcript.txt'
MARKERS = FIXTURES / 'markers.txt'


def run(transcript, markers, *extra):
    return run_script(SCRIPT, '--transcript', transcript, '--markers', markers, *extra)


def markers_file(tmp_path, text):
    path = tmp_path / 'markers.txt'
    path.write_text(text, encoding='utf-8')
    return path


@pytest.mark.parametrize('transcript', [VTT, TXT], ids=['vtt', 'txt'])
def test_fixture_meeting_passes_with_warnings_and_lists_the_unmarked_commitment(transcript):
    result = run(transcript, MARKERS, '--recording-start', '19:30')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'OVERALL VERDICT: PASS WITH WARNINGS' in result.stdout
    assert 'WARN     marker 19:52: inaudible or crosstalk inside its window' in result.stdout
    assert '1 unmarked stretch(es) of speech' in result.stdout
    assert '(clock 19:40–19:43)' in result.stdout
    assert 'I second that.' in result.stdout


@pytest.mark.parametrize('transcript', [VTT, TXT], ids=['vtt', 'txt'])
def test_speaker_labels_are_always_printed_as_unconfirmed(transcript):
    result = run(transcript, MARKERS, '--recording-start', '19:30')
    excerpt_lines = [l for l in result.stdout.splitlines() if l.startswith('- [')]
    assert excerpt_lines
    for line in excerpt_lines:
        assert '(unconfirmed label: ' in line or '(no speaker label)' in line, line


def test_unmarked_speech_never_appears_as_an_excerpt():
    result = run(VTT, MARKERS, '--recording-start', '19:30')
    excerpts = '\n'.join(l for l in result.stdout.splitlines() if l.startswith('- ['))
    assert 'raise it with the town council' not in excerpts


def test_clean_meeting_passes(tmp_path):
    transcript = tmp_path / 't.txt'
    transcript.write_text('[00:00:10] Alice Lim: The meeting is called to order.\n', encoding='utf-8')
    result = run(transcript, markers_file(tmp_path, '19:30 Call to order\n'), '--recording-start', '19:30')
    assert result.returncode == 0, result.stdout
    assert 'OVERALL VERDICT: PASS\n' in result.stdout + '\n'


def test_offset_markers_work_without_a_start_time(tmp_path):
    result = run(VTT, markers_file(tmp_path, '+05:00 Minutes confirmed\n'))
    assert result.returncode == 0, result.stdout
    assert 'I second that.' in result.stdout


def test_srt_transcripts_are_read(tmp_path):
    srt = tmp_path / 't.srt'
    srt.write_text('1\n00:00:05,000 --> 00:00:12,000\nAlice Lim: Good evening.\n\n', encoding='utf-8')
    result = run(srt, markers_file(tmp_path, '+00:08 Opening\n'))
    assert result.returncode == 0, result.stdout
    assert '(unconfirmed label: Alice Lim) Good evening.' in result.stdout


# --- fail closed ---------------------------------------------------------------

def test_empty_markers_file_fails(tmp_path):
    result = run(VTT, markers_file(tmp_path, '# no markers yet\n\n'), '--recording-start', '19:30')
    assert result.returncode == 1
    assert 'OVERALL VERDICT: FAIL' in result.stdout
    assert 'the markers file has no markers' in result.stdout


def test_marker_before_the_recording_started_fails(tmp_path):
    result = run(VTT, markers_file(tmp_path, '19:20 Pre-meeting chat\n'), '--recording-start', '19:30')
    assert result.returncode == 1
    assert 'BLOCKER  marker 19:20 falls outside the recording (0:00:00–0:41:20, clock 19:30–20:11)' in result.stdout


def test_marker_in_a_silent_stretch_fails(tmp_path):
    result = run(VTT, markers_file(tmp_path, '20:03 Something I thought I heard\n'), '--recording-start', '19:30')
    assert result.returncode == 1
    assert 'BLOCKER  marker 20:03 has no usable speech within ±3 min' in result.stdout


def test_window_holding_only_inaudible_speech_fails(tmp_path):
    transcript = tmp_path / 't.txt'
    transcript.write_text('[00:00:10] Speaker 2: [inaudible]\n[00:20:00] Alice Lim: Closing.\n',
                          encoding='utf-8')
    result = run(transcript, markers_file(tmp_path, '+00:10 Agency commitment\n'))
    assert result.returncode == 1
    assert 'BLOCKER  marker +00:10 has no usable speech' in result.stdout


def test_docx_transcript_is_refused_with_a_conversion_hint(tmp_path):
    docx = tmp_path / 'transcript.docx'
    docx.write_bytes(b'PK\x03\x04')
    result = run(docx, MARKERS, '--recording-start', '19:30')
    assert result.returncode == 1
    assert "unsupported transcript format '.docx'" in result.stdout
    assert 'convert it to .vtt, .srt or a timestamped .txt' in result.stdout


def test_clock_markers_without_a_start_time_fail():
    result = run(VTT, MARKERS)
    assert result.returncode == 1
    assert 'clock-time markers need --recording-start' in result.stdout


def test_a_mistyped_marker_is_a_blocker_not_silently_skipped(tmp_path):
    result = run(VTT, markers_file(tmp_path, '19:35 Minutes confirmed\n19.52 Agency update\n'),
                 '--recording-start', '19:30')
    assert result.returncode == 1
    assert 'markers line 2 is not a marker' in result.stdout


def test_vtt_without_header_fails(tmp_path):
    bad = tmp_path / 't.vtt'
    bad.write_text('00:00:05.000 --> 00:00:12.000\nHello\n', encoding='utf-8')
    result = run(bad, markers_file(tmp_path, '+00:08 Opening\n'))
    assert result.returncode == 1
    assert 'must start with WEBVTT' in result.stdout
