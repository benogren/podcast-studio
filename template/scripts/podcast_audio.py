"""Shared post-render step for the local renderers (Kokoro, Orpheus, Gemini):
wrap the rendered dialogue in the show's theme music, then loudness-master
and encode the MP3.

Layout, modeled on MFM (cold open, then theme, then the show):

    [cold-open teaser] [pause] [intro theme ........\\fade]
                                             [restart line → rest of episode]
    ... "that's the pod." [pause] [outro theme /fade in ... fade\\]

The intro's fade-out overlaps the first words of the restart so the music
hands off rather than stopping dead. With no cold open marked, the intro
plays at the very start.

Mastering runs ffmpeg's loudnorm filter to the podcast norm (-16 LUFS,
-1.5 dBTP true peak). That keeps the theme and voices at a consistent level
across episodes and renderers, and removes the inter-sample overs Gemini's
raw output carries (+2.5 dBTP measured 2026-09-28).

Music files live in assets/: intro.mp3 and outro.mp3 if present,
otherwise theme.mp3 for both.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"

SAMPLE_RATE = 24000

# Theme level relative to the dialogue's average loudness (dB). Measured
# LUFS of the theme and the speech are within a dB, so this is a small trim.
MUSIC_GAIN_DB = -3.0
INTRO_FADE_IN_MS = 150
INTRO_FADE_OUT_MS = 2500
# How far the restart line starts before the intro ends (inside the fade).
INTRO_OVERLAP_MS = 1500
COLD_OPEN_PAUSE_MS = 400
OUTRO_PAUSE_MS = 700
OUTRO_FADE_IN_MS = 800
OUTRO_FADE_OUT_MS = 3000

TARGET_LUFS = -16
TARGET_TRUE_PEAK = -1.5
TARGET_LRA = 11
MP3_BITRATE = "128k"


def _music_path(kind):
    specific = ASSETS_DIR / f"{kind}.mp3"
    if specific.exists():
        return specific
    theme = ASSETS_DIR / "theme.mp3"
    return theme if theme.exists() else None


def _load_music(path, target_dbfs):
    from pydub import AudioSegment
    from pydub.silence import detect_leading_silence

    seg = AudioSegment.from_file(path).set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)
    # Trim leading/trailing silence so fades and overlaps are timed on music.
    start = detect_leading_silence(seg, silence_threshold=-45.0)
    end = detect_leading_silence(seg.reverse(), silence_threshold=-45.0)
    seg = seg[start : len(seg) - end]
    return seg.apply_gain(target_dbfs - seg.dBFS)


def add_music(voice, cold_open_ms=None):
    """Return voice wrapped in intro/outro theme. voice is a 24 kHz mono
    16-bit pydub AudioSegment; cold_open_ms is where the teaser ends (the
    intro goes there), or None to put the intro at the start."""
    from pydub import AudioSegment

    intro_path, outro_path = _music_path("intro"), _music_path("outro")
    if not intro_path and not outro_path:
        print(f"  (no theme music in {ASSETS_DIR}; skipping music)", file=sys.stderr)
        return voice

    level = voice.dBFS + MUSIC_GAIN_DB
    head = AudioSegment.empty()
    body = voice
    if cold_open_ms:
        head = voice[:cold_open_ms] + AudioSegment.silent(COLD_OPEN_PAUSE_MS, frame_rate=SAMPLE_RATE)
        body = voice[cold_open_ms:]

    intro = AudioSegment.empty()
    if intro_path:
        intro = _load_music(intro_path, level).fade_in(INTRO_FADE_IN_MS).fade_out(INTRO_FADE_OUT_MS)
    body_start = len(head) + max(len(intro) - INTRO_OVERLAP_MS, 0)

    outro = AudioSegment.empty()
    if outro_path:
        outro = _load_music(outro_path, level).fade_in(OUTRO_FADE_IN_MS).fade_out(OUTRO_FADE_OUT_MS)
    outro_start = body_start + len(body) + OUTRO_PAUSE_MS

    total = outro_start + len(outro) if len(outro) else body_start + len(body)
    mix = AudioSegment.silent(total, frame_rate=SAMPLE_RATE).set_sample_width(2)
    mix = mix.overlay(head, position=0)
    if len(intro):
        mix = mix.overlay(intro, position=len(head))
    mix = mix.overlay(body, position=body_start)
    if len(outro):
        mix = mix.overlay(outro, position=outro_start)
    print(
        f"  theme: intro {len(intro) / 1000:.1f}s at {len(head) / 1000:.1f}s"
        + (f", outro {len(outro) / 1000:.1f}s" if len(outro) else ""),
        file=sys.stderr,
    )
    return mix


def master_mp3(segment):
    """Loudness-normalize and encode to MP3. Returns (mp3_bytes,
    duration_seconds). Exits 5 on ffmpeg failure, like the renderers."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.wav"
        dst = Path(tmp) / "out.mp3"
        segment.export(src, format="wav")
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
            "-af", f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TRUE_PEAK}:LRA={TARGET_LRA}",
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-b:a", MP3_BITRATE, str(dst),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except FileNotFoundError:
            print("ERROR: ffmpeg not found (brew install ffmpeg)", file=sys.stderr)
            sys.exit(5)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: ffmpeg mastering failed: {e.stderr.decode()[:500]}", file=sys.stderr)
            sys.exit(5)
        return dst.read_bytes(), len(segment) / 1000


def finish_episode(voice, cold_open_ms=None, music=True):
    """add_music (unless music=False) then master_mp3."""
    if music:
        voice = add_music(voice, cold_open_ms)
    return master_mp3(voice)


def segment_from_int16(samples):
    """Wrap a mono int16 numpy array as a 24 kHz pydub segment."""
    from pydub import AudioSegment

    return AudioSegment(samples.tobytes(), frame_rate=SAMPLE_RATE, sample_width=2, channels=1)


def validate_cold_open(payload):
    """Error strings for the optional cold_open_lines field: the number of
    leading dialogue lines that form the cold-open teaser (the intro theme
    plays after them)."""
    if "cold_open_lines" not in payload:
        return []
    n = payload["cold_open_lines"]
    dialogue = payload.get("dialogue") or []
    if not isinstance(n, int) or isinstance(n, bool) or not (1 <= n < max(len(dialogue), 1)):
        return [f"cold_open_lines must be an integer from 1 to {max(len(dialogue) - 1, 1)}"]
    return []
