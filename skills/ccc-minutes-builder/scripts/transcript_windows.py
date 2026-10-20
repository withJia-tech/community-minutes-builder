#!/usr/bin/env python3
"""Cut a meeting transcript down to the secretary's marked moments.

    python transcript_windows.py --transcript meeting.vtt --markers markers.txt \
        --recording-start 19:30

A transcript records what was said, not what was decided. The secretary's
markers ("21:14 NEA commitment, hit rates owed") decide which moments may
feed the minutes. This script prints the transcript lines inside each
marker's window and lists unmarked stretches of speech as suggestions only.

Fails closed (exit 1): an empty or unreadable markers file, an unsupported
transcript format, a marker line it cannot read, clock markers without
--recording-start, a marker outside the recording, or a window with no
usable speech.
"""
import argparse
import re
import sys
from pathlib import Path

DAY = 24 * 3600
TXT_CUE_SECONDS = 30   # a .txt line has no end time; assume at most this long
STRETCH_GAP_SECONDS = 120  # pauses shorter than this join one unmarked stretch

GAP = re.compile(r'[\[(](?:inaudible|crosstalk|unintelligible|indistinct)[^\])]*[\])]', re.I)
TIMING = re.compile(
    r'^\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})')
VOICE = re.compile(r'<v(?:\.[^\s>]*)?\s+([^>]+)>')
TAG = re.compile(r'</?[^>]+>')
TXT_LINE = re.compile(r'^\[(\d{1,2}(?::\d{2}){1,2})\]\s*(.*)$')
SPEAKER = re.compile(r"^([A-Z][\w.'-]*(?: [A-Z0-9][\w.'-]*){0,3}):\s+(.*)$")
CLOCK_MARKER = re.compile(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?(?=\s|$)\s*(.*)$')
OFFSET_MARKER = re.compile(r'^\+(\d{1,2}(?::\d{2}){1,2})(?=\s|$)\s*(.*)$')


class TranscriptError(Exception):
    pass


def colon_seconds(stamp):
    """'MM:SS' or 'H:MM:SS' to seconds; minutes and seconds must be < 60."""
    parts = [int(p) for p in stamp.split(':')]
    if len(parts) == 2:
        hours, (mins, secs) = 0, parts
    else:
        hours, mins, secs = parts
    if mins > 59 or secs > 59:
        raise ValueError(stamp)
    return hours * 3600 + mins * 60 + secs


def cue_seconds(stamp):
    parts = stamp.replace(',', '.').split(':')
    hours = int(parts[0]) if len(parts) == 3 else 0
    return hours * 3600 + int(parts[-2]) * 60 + float(parts[-1])


def parse_clock(value):
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(?::(\d{2}))?', value.strip())
    if not m:
        raise ValueError(value)
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    if h > 23 or mi > 59 or s > 59:
        raise ValueError(value)
    return h * 3600 + mi * 60 + s


def split_speaker(text):
    m = SPEAKER.match(text)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, text)


def parse_cues(text, require_header):
    """WebVTT (.vtt) or SubRip (.srt) cues."""
    lines = text.splitlines()
    if require_header and not (lines and lines[0].strip().startswith('WEBVTT')):
        raise TranscriptError('a .vtt transcript must start with WEBVTT')
    cues, i = [], 0
    while i < len(lines):
        m = TIMING.match(lines[i])
        i += 1
        if not m:
            continue
        start, end = cue_seconds(m.group(1)), cue_seconds(m.group(2))
        if end < start:
            raise TranscriptError('cue ends before it starts at %s' % m.group(1))
        body = []
        while i < len(lines) and lines[i].strip():
            body.append(lines[i])
            i += 1
        raw = ' '.join(body)
        voice = VOICE.search(raw)
        words = ' '.join(TAG.sub('', raw).split())
        if voice:
            speaker = voice.group(1).strip()
        else:
            speaker, words = split_speaker(words)
        cues.append({'start': start, 'end': end, 'speaker': speaker, 'text': words})
    return cues


def parse_txt(text):
    """Lines like '[00:41:12] Speaker: text'; untimed lines continue the last cue."""
    cues = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = TXT_LINE.match(line)
        if m:
            try:
                start = colon_seconds(m.group(1))
            except ValueError:
                raise TranscriptError('bad timestamp [%s]' % m.group(1))
            speaker, words = split_speaker(m.group(2).strip())
            cues.append({'start': start, 'end': start, 'speaker': speaker, 'text': words})
        elif cues:
            cues[-1]['text'] = (cues[-1]['text'] + ' ' + line).strip()
        else:
            raise TranscriptError('text before the first [hh:mm:ss] timestamp: %r' % line[:60])
    for before, after in zip(cues, cues[1:]):
        if after['start'] < before['start']:
            raise TranscriptError('timestamps go backwards at [%s]' % fmt_offset(after['start']))
        before['end'] = min(after['start'], before['start'] + TXT_CUE_SECONDS)
    return cues


def load_transcript(path):
    suffix = path.suffix.lower()
    if suffix not in ('.vtt', '.srt', '.txt'):
        raise TranscriptError(
            'unsupported transcript format %r: export or convert it to .vtt, .srt '
            'or a timestamped .txt' % (suffix or 'no extension'))
    try:
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeDecodeError) as exc:
        raise TranscriptError('cannot read transcript: %s' % exc)
    cues = parse_txt(text) if suffix == '.txt' else parse_cues(text, suffix == '.vtt')
    if not cues:
        raise TranscriptError('no timed lines found in %s' % path.name)
    return sorted(cues, key=lambda c: c['start'])


def load_markers(path, start):
    """Return (markers, problems). Every unreadable line is a problem, never skipped."""
    try:
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeDecodeError) as exc:
        return [], ['cannot read markers: %s' % exc]
    markers, problems, needs_start = [], [], False
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        m = OFFSET_MARKER.match(line)
        if m:
            try:
                offset = colon_seconds(m.group(1))
            except ValueError:
                problems.append('markers line %d has an impossible time: %r' % (lineno, line[:60]))
                continue
            markers.append({'label': '+' + m.group(1), 'offset': offset,
                            'note': m.group(2).lstrip('-–— ').strip()})
            continue
        m = CLOCK_MARKER.match(line)
        if m:
            try:
                clock = parse_clock(line[:m.end(3) if m.group(3) else m.end(2)])
            except ValueError:
                problems.append('markers line %d has an impossible time: %r' % (lineno, line[:60]))
                continue
            if start is None:
                needs_start = True
                continue
            markers.append({'label': line.split()[0], 'offset': (clock - start) % DAY,
                            'note': m.group(4).lstrip('-–— ').strip()})
            continue
        problems.append('markers line %d is not a marker (expected "HH:MM note" or '
                        '"+MM:SS note"): %r' % (lineno, line[:60]))
    if needs_start:
        problems.append('clock-time markers need --recording-start HH:MM to line them up '
                        'with the transcript')
    if not markers and not problems:
        problems.append('the markers file has no markers. The secretary decides what enters '
                        'the minutes, so a transcript cannot be used without them')
    return markers, problems


def fmt_offset(seconds):
    seconds = int(round(seconds))
    return '%d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


def fmt_clock(start, offset):
    if start is None:
        return '—'
    t = int(round(start + offset)) % DAY
    return '%02d:%02d' % (t // 3600, t % 3600 // 60)


def usable(cue):
    return bool(GAP.sub('', cue['text']).strip())


def overlaps(cue, lo, hi):
    return cue['end'] >= lo and cue['start'] <= hi


def who(cue):
    if cue['speaker']:
        return '(unconfirmed label: %s)' % cue['speaker']
    return '(no speaker label)'


def safe(text):
    return text.replace('|', '/')


def report(blockers, warnings):
    verdict = 'FAIL' if blockers else ('PASS WITH WARNINGS' if warnings else 'PASS')
    print('\nOVERALL VERDICT: %s' % verdict)
    for item in blockers:
        print('BLOCKER  %s' % item)
    for item in warnings:
        print('WARN     %s' % item)
    return 1 if blockers else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Cut a transcript to the secretary\'s marked moments.')
    ap.add_argument('--transcript', required=True, help='.vtt, .srt or timestamped .txt')
    ap.add_argument('--markers', required=True, help='one "HH:MM note" or "+MM:SS note" per line')
    ap.add_argument('--recording-start', help='wall-clock time the recording began, e.g. 19:30')
    ap.add_argument('--window', type=float, default=3.0,
                    help='minutes of transcript either side of each marker (default 3)')
    ap.add_argument('--unmarked-min', type=float, default=2.0,
                    help='list unmarked speech lasting at least this many minutes (default 2)')
    a = ap.parse_args(argv)

    blockers, warnings = [], []
    start = None
    if a.recording_start:
        try:
            start = parse_clock(a.recording_start)
        except ValueError:
            blockers.append('--recording-start %r is not a time like 19:30' % a.recording_start)
    if a.window <= 0 or a.unmarked_min <= 0:
        blockers.append('--window and --unmarked-min must be positive')

    try:
        cues = load_transcript(Path(a.transcript))
    except TranscriptError as exc:
        blockers.append(str(exc))
        cues = []
    markers, problems = load_markers(Path(a.markers), start)
    blockers.extend(problems)
    if not cues or not markers:
        return report(blockers, warnings)

    window = a.window * 60
    rec_end = max(c['end'] for c in cues)
    covered = []
    excerpts = []

    print('| Marker | Note | Recording window | Clock window | Signal |')
    print('|---|---|---|---|---|')
    for marker in markers:
        off = marker['offset']
        name = '%s %s' % (marker['label'], marker['note'])
        if off > rec_end:
            blockers.append('marker %s falls outside the recording (0:00:00–%s, clock %s–%s)'
                            % (marker['label'], fmt_offset(rec_end), fmt_clock(start, 0),
                               fmt_clock(start, rec_end)))
            print('| %s | %s | — | — | outside the recording |'
                  % (marker['label'], safe(marker['note'])))
            continue
        lo, hi = max(0, off - window), min(rec_end, off + window)
        in_window = [c for c in cues if overlaps(c, lo, hi)]
        signals = []
        if not any(usable(c) for c in in_window):
            blockers.append('marker %s has no usable speech within ±%g min'
                            % (marker['label'], a.window))
            signals.append('no usable speech')
        if any(GAP.search(c['text']) for c in in_window):
            warnings.append('marker %s: inaudible or crosstalk inside its window; do not '
                            'reconstruct it, mark [TBC] if the item depends on it'
                            % marker['label'])
            signals.append('inaudible/crosstalk')
        covered.append((lo, hi))
        excerpts.append((name, lo, hi, in_window))
        print('| %s | %s | %s–%s | %s–%s | %s |'
              % (marker['label'], safe(marker['note']), fmt_offset(lo), fmt_offset(hi),
                 fmt_clock(start, lo), fmt_clock(start, hi), '; '.join(signals) or 'ok'))

    for name, lo, hi, in_window in excerpts:
        print('\n#### %s' % safe(name))
        print('window %s–%s (clock %s–%s)'
              % (fmt_offset(lo), fmt_offset(hi), fmt_clock(start, lo), fmt_clock(start, hi)))
        for cue in in_window:
            print('- [%s] %s %s' % (fmt_offset(cue['start']), who(cue), safe(cue['text'])))

    stretches, current = [], []
    for cue in cues:
        if not usable(cue) or any(overlaps(cue, lo, hi) for lo, hi in covered):
            continue
        if current and cue['start'] - current[-1]['end'] > STRETCH_GAP_SECONDS:
            stretches.append(current)
            current = []
        current.append(cue)
    if current:
        stretches.append(current)
    long_ones = [s for s in stretches if s[-1]['end'] - s[0]['start'] >= a.unmarked_min * 60]

    print('\nUnmarked stretches (suggestions only, not sources):')
    if not long_ones:
        print('- none')
    for s in long_ones:
        labels = sorted({c['speaker'] for c in s if c['speaker']})
        print('- %s–%s (clock %s–%s), %d words, labels (unconfirmed): %s'
              % (fmt_offset(s[0]['start']), fmt_offset(s[-1]['end']),
                 fmt_clock(start, s[0]['start']), fmt_clock(start, s[-1]['end']),
                 sum(len(c['text'].split()) for c in s), ', '.join(labels) or 'none'))
    if long_ones:
        warnings.append('%d unmarked stretch(es) of speech: possible items for the drafter to '
                        'decide; none may enter the minutes without a marker or note'
                        % len(long_ones))

    print('\nA transcript shows what was said, not what was decided. Speaker labels and '
          'names heard in audio are unconfirmed until matched to the attendance sheet.')
    return report(blockers, warnings)


if __name__ == '__main__':
    sys.exit(main())
