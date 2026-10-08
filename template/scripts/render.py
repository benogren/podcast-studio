#!/usr/bin/env python3
"""Render a podcast episode payload to a local MP3 with Gemini multi-speaker TTS.

The payload is a JSON file (see SPEC/style-guide.md, "Payload"):

    {"title": "...", "description": "...", "cold_open_lines": 3,
     "dialogue": [{"speaker": "host"|"guest"|"intern", "text": "..."}, ...],
     "source_refs": ["..."]}

Voices come from show.json (hosts.host.voice, hosts.guest.voice, hosts.intern.voice),
overridable per run with --host-voice / --guest-voice / --intern-voice.
GEMINI_API_KEY comes from the environment or from .env.local next to this project.

Gemini voices at most two speakers per request, so consecutive turns are packed into
chunks of <= 500 words and at most two distinct speakers (a turn is never split). Write
intern episodes in two-voice segments so the chunk seams fall at hand-offs. Chunks are
stitched with a short silence, wrapped in optional theme music after the cold open, and
loudness-mastered to -16 LUFS (needs ffmpeg).

Usage:
    python scripts/render.py --validate payloads/EPISODE.json   # no API call, free
    python scripts/render.py --max-lines 6 payloads/EPISODE.json # cheap smoke test
    python scripts/render.py payloads/EPISODE.json               # full render
    python scripts/render.py --no-music payloads/EPISODE.json

Exit codes: 0 ok, 1 validation, 2 API client error, 3 API server error (or 429 after
retries), 4 config / dependency / network, 5 audio decode or encode.
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env.local"
SHOW_PATH = PROJECT_ROOT / "show.json"
AUDIO_DIR = PROJECT_ROOT / "audio"

sys.path.insert(0, str(SCRIPT_DIR))
from tts_text import normalize_years
from podcast_audio import finish_episode, validate_cold_open

API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_MODEL = "gemini-3.8-flash-tts"

SAMPLE_RATE = 24000
SILENCE_MS = 250

SPEAKERS = {"host", "guest", "intern"}
DEFAULT_VOICES = {"host": "Sulafat", "guest": "Algenib", "intern": "Zephyr"}

# Speaker labels sent to the API; never spoken aloud.
SPEAKER_LABELS = {"host": "Host", "guest": "Guest", "intern": "Intern"}

DEFAULT_STYLE = "natural, energetic podcast conversation between two friends"
SPEAKER_STYLES = {
    "intern": "curious, clear, quick, excited to explain what she just learned, on a podcast with two friends",
}

TITLE_MAX, DESC_MAX, DIALOGUE_MAX, LINE_MAX = 200, 500, 500, 2000
MAX_WORDS_PER_CHUNK = 500
MAX_RETRIES = 4
REQUEST_TIMEOUT = 300

# Introductory pricing, USD per million tokens (re-check before relying on it:
# https://ai.google.dev/pricing). Used only for the printed estimate.
PRICE_INPUT_PER_M = 0.75
PRICE_OUTPUT_PER_M = 3.75


# ---------------------------------------------------------------- config

def load_show():
    if SHOW_PATH.exists():
        try:
            return json.loads(SHOW_PATH.read_text())
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON in {SHOW_PATH}: {e}", file=sys.stderr)
            sys.exit(4)
    return {}


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        print(
            "ERROR: GEMINI_API_KEY not set. Put it in .env.local (copy .env.local.example) "
            "or export it. Get a key at https://aistudio.google.com/apikey",
            file=sys.stderr,
        )
        sys.exit(4)
    return key


def resolve_voices(show, args):
    hosts = show.get("hosts", {})
    return {
        sp: (getattr(args, f"{sp}_voice") or hosts.get(sp, {}).get("voice") or DEFAULT_VOICES[sp])
        for sp in ("host", "guest", "intern")
    }


# ---------------------------------------------------------------- validation

# TTS reads text literally; these written-notation habits come out mangled.
_TTS_HOSTILE = [
    (re.compile(r"[$€£]\s?\d"), "currency symbol ($4M); write 'four million dollars'"),
    (re.compile(r"\d\s?%"), "percent sign; write 'twelve percent'"),
    (re.compile(r"\b\d+(\.\d+)?\s?[xX]\b"), "'3x'; write 'three times'"),
    (re.compile(r"\bQ[1-4]\b"), "'Q1'; write 'first quarter'"),
    (re.compile(r"\b\d+\s?[-–]\s?\d+\b"), "digit range or score ('7-4'); write 'seven to four'"),
    (re.compile(r"https?://|www\."), "URL; never read a URL aloud"),
    (re.compile(r"[*_#`\[\]]"), "markdown characters; dialogue is plain spoken text"),
]


def _persona_similarity_warnings():
    """Warn when two persona files are near-duplicates: the #1 reason hosts blur together."""
    import difflib
    out = []
    names = ["host", "guest", "intern"]
    texts = {}
    for sp in names:
        rel = load_show().get("hosts", {}).get(sp, {}).get("persona")
        f = PROJECT_ROOT / rel if rel else None
        if f and f.exists():
            texts[sp] = re.sub(r"\b(?:Alex|Sam|Riley)\b", "X", f.read_text())
    keys = list(texts)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ratio = difflib.SequenceMatcher(None, texts[a], texts[b]).ratio()
            if ratio > 0.6:
                out.append(f"persona files for '{a}' and '{b}' are {ratio:.0%} alike; "
                           "rewrite them so the voices differ in priors, pace, humor and role")
    return out


def validate_payload(payload):
    """Returns (errors, warnings). Errors block rendering; warnings are style lint."""
    errors, warnings = [], []
    title = payload.get("title")
    if not isinstance(title, str) or not (1 <= len(title) <= TITLE_MAX):
        errors.append(f"title must be a string, 1-{TITLE_MAX} chars")
    desc = payload.get("description")
    if not isinstance(desc, str) or not (1 <= len(desc) <= DESC_MAX):
        errors.append(f"description must be a string, 1-{DESC_MAX} chars")
    dialogue = payload.get("dialogue")
    if not isinstance(dialogue, list):
        errors.append("dialogue must be an array")
        return errors, warnings
    if not (1 <= len(dialogue) <= DIALOGUE_MAX):
        errors.append(f"dialogue must have 1-{DIALOGUE_MAX} items (got {len(dialogue)})")
        return errors, warnings
    for i, item in enumerate(dialogue):
        if not isinstance(item, dict):
            errors.append(f"dialogue[{i}] must be an object")
            continue
        if item.get("speaker") not in SPEAKERS:
            errors.append(f"dialogue[{i}].speaker must be one of {sorted(SPEAKERS)} (got {item.get('speaker')!r})")
        text = item.get("text")
        if not isinstance(text, str) or not (1 <= len(text) <= LINE_MAX):
            errors.append(f"dialogue[{i}].text must be a string, 1-{LINE_MAX} chars")
    if "source_refs" in payload:
        refs = payload["source_refs"]
        if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
            errors.append("source_refs must be an array of strings")
    errors += validate_cold_open(payload)
    if errors:
        return errors, warnings

    # ---- style lint (warnings only)
    run = 1
    for i, line in enumerate(dialogue):
        text = line["text"]
        if i and dialogue[i - 1]["speaker"] == line["speaker"]:
            run += 1
            if run == 5:
                warnings.append(f"dialogue[{i}]: 5+ consecutive lines from '{line['speaker']}'; add an interjection")
        else:
            run = 1
        if len(text.split()) <= 1:
            warnings.append(f"dialogue[{i}]: one-word line ({text!r}); give it a tail or cut it")
        for rx, why in _TTS_HOSTILE:
            if rx.search(text):
                warnings.append(f"dialogue[{i}]: {why}")
                break
    words = sum(len(l["text"].split()) for l in dialogue)
    lengths = [len(l["text"].split()) for l in dialogue]
    if len(dialogue) >= 20 and max(lengths) - min(lengths) < 25:
        warnings.append("line lengths are very uniform; vary lead lines and burst lines")
    warnings += _persona_similarity_warnings()
    meta = payload.get("meta")
    if not isinstance(meta, dict) or not all(meta.get(k) for k in ("type", "spine", "lead")):
        warnings.append("payload has no complete `meta` (type, spine, lead); rotation.py can't count this episode. See SPEC/episode-types.md")
    show = load_show()
    lo, hi = (show.get("target_words") or [0, 0])[:2] if isinstance(show.get("target_words"), list) else (0, 0)
    if len(dialogue) < 20:
        lo = hi = 0  # tiny payloads (smoke tests, samples) skip the length check
    if lo and words < lo * 0.7:
        warnings.append(f"{words} words is well under the target ({lo}-{hi}); is the material fully covered?")
    if hi and words > hi * 1.3:
        warnings.append(f"{words} words is well over the target ({lo}-{hi}); cut padding")
    return errors, warnings


# ---------------------------------------------------------------- Gemini

def chunk_dialogue(dialogue, max_words=MAX_WORDS_PER_CHUNK, break_after=None):
    """Greedy-pack whole turns into chunks of <= max_words with at most two
    distinct speakers. A third speaker starts a new chunk. break_after=N forces
    a boundary after line N (the cold open) so the intro theme lands there."""
    chunks, buf, words, speakers = [], [], 0, set()
    for idx, line in enumerate(dialogue):
        w = len(line["text"].split())
        new_speakers = speakers | {line["speaker"]}
        if buf and (words + w > max_words or len(new_speakers) > 2 or idx == break_after):
            chunks.append(buf)
            buf, words, new_speakers = [], 0, {line["speaker"]}
        buf.append(line)
        words += w
        speakers = new_speakers
    if buf:
        chunks.append(buf)
    return chunks


def build_request(model, lines, voices):
    """The API requires exactly two declared speakers even when only one talks,
    so a one-speaker chunk declares a second, silent one."""
    content = [
        {
            "type": "text",
            "text": normalize_years(line["text"]),
            "annotations": [
                {
                    "type": "speech_metadata",
                    "speaker": SPEAKER_LABELS[line["speaker"]],
                    "style": SPEAKER_STYLES.get(line["speaker"], DEFAULT_STYLE),
                }
            ],
        }
        for line in lines
    ]
    present = list(dict.fromkeys(line["speaker"] for line in lines))
    for filler in ("host", "guest", "intern"):
        if len(present) >= 2:
            break
        if filler not in present:
            present.append(filler)
    return {
        "model": model,
        "input": [{"type": "user_input", "content": content}],
        "response_format": {"type": "audio"},
        "generation_config": {
            "speech_config": {
                "mode": "conversational",
                "speakers": [{"speaker": SPEAKER_LABELS[sp], "voice": voices[sp]} for sp in present],
            }
        },
    }


def _find_audio_b64(obj):
    parts = []
    for step in obj.get("steps", []) or []:
        for item in step.get("content", []) or []:
            if isinstance(item, dict) and item.get("type") == "audio" and item.get("data"):
                parts.append(item["data"])
    audio = obj.get("output_audio") or obj.get("outputAudio")
    if not parts and isinstance(audio, dict) and audio.get("data"):
        parts.append(audio["data"])
    return parts


def _usage_tokens(obj):
    usage = obj.get("usage") or obj.get("usage_metadata") or obj.get("usageMetadata") or {}
    inp = usage.get("total_input_tokens") or usage.get("input_tokens") or usage.get("promptTokenCount") or 0
    out = usage.get("total_output_tokens") or usage.get("output_tokens") or usage.get("candidatesTokenCount") or 0
    return int(inp), int(out)


def call_gemini(api_key, body, idx):
    import requests

    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(API_URL, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES:
                print(f"ERROR: chunk[{idx}] network: {e}", file=sys.stderr)
                sys.exit(4)
            time.sleep(2**attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt == MAX_RETRIES:
                print(f"ERROR: chunk[{idx}] HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
                sys.exit(3)
            wait = 2**attempt * 2
            print(f"  chunk[{idx}] HTTP {resp.status_code}, retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code >= 400:
            print(f"ERROR: chunk[{idx}] HTTP {resp.status_code}: {resp.text[:1000]}", file=sys.stderr)
            sys.exit(2)
        return resp.json()


def decode_audio(b64, idx):
    from pydub import AudioSegment

    raw = base64.b64decode(b64)
    try:
        if raw[:4] == b"RIFF":
            seg = AudioSegment.from_file(io.BytesIO(raw), format="wav")
        else:
            seg = AudioSegment(raw, frame_rate=SAMPLE_RATE, sample_width=2, channels=1)
    except Exception as e:
        print(f"ERROR: chunk[{idx}] audio decode failed: {e}", file=sys.stderr)
        sys.exit(5)
    if seg.frame_rate != SAMPLE_RATE or seg.channels != 1 or seg.sample_width != 2:
        seg = seg.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)
    return seg


def render_dialogue(dialogue, api_key, model, voices, cold_open_lines=None):
    """Returns (segment, tokens_in, tokens_out, cold_open_ms)."""
    from pydub import AudioSegment

    chunks = chunk_dialogue(dialogue, break_after=cold_open_lines)
    cold_open_ms = None
    lines_done = 0
    silence = AudioSegment.silent(duration=SILENCE_MS, frame_rate=SAMPLE_RATE).set_sample_width(2)
    full = AudioSegment.empty()
    total_in = total_out = 0
    for i, lines in enumerate(chunks):
        words = sum(len(l["text"].split()) for l in lines)
        t = time.time()
        data = call_gemini(api_key, build_request(model, lines, voices), i)
        parts = _find_audio_b64(data)
        if not parts:
            print(f"ERROR: chunk[{i}] response had no audio. Keys: {sorted(data.keys())}", file=sys.stderr)
            sys.exit(5)
        seg = sum((decode_audio(p, i) for p in parts[1:]), decode_audio(parts[0], i))
        inp, out = _usage_tokens(data)
        total_in += inp
        total_out += out
        full += seg
        lines_done += len(lines)
        if cold_open_lines and lines_done == cold_open_lines:
            cold_open_ms = len(full)
        if i < len(chunks) - 1:
            full += silence
        who = "+".join(dict.fromkeys(l["speaker"] for l in lines))
        print(
            f"  [{i + 1}/{len(chunks)}] {who}: {len(lines)} turns, {words} words -> {len(seg) / 1000:.1f}s "
            f"audio in {time.time() - t:.1f}s",
            file=sys.stderr,
        )
    return full, total_in, total_out, cold_open_ms


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("payload_path", help="Path to the episode JSON payload")
    parser.add_argument("--validate", action="store_true", help="Validate and lint only; no API call")
    parser.add_argument("--out", help="Output MP3 path (default: audio/<payload-name>.mp3)")
    parser.add_argument("--no-music", action="store_true", help="Skip the intro/outro theme (still mastered)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"TTS model ID (default {DEFAULT_MODEL})")
    parser.add_argument("--host-voice", help="Prebuilt voice for host (default: show.json)")
    parser.add_argument("--guest-voice", help="Prebuilt voice for guest (default: show.json)")
    parser.add_argument("--intern-voice", help="Prebuilt voice for intern (default: show.json)")
    parser.add_argument("--max-lines", type=int, default=0,
                        help="Render only the first N lines (smoke test); writes audio/smoke-*.mp3")
    args = parser.parse_args()

    path = Path(args.payload_path)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(4)
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)

    errors, warnings = validate_payload(payload)
    if errors:
        print(f"Validation failed for {path}:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    if warnings:
        print(f"Style warnings for {path} (not blocking):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
    words = sum(len(l["text"].split()) for l in payload["dialogue"])
    if args.validate:
        print(f"OK: {path} is valid ({len(payload['dialogue'])} lines, {words} words, ~{words / 150:.0f} min)")
        sys.exit(0)

    dialogue = payload["dialogue"]
    if args.max_lines > 0:
        dialogue = dialogue[: args.max_lines]
        print(f"--max-lines {args.max_lines}: rendering first {len(dialogue)} of {len(payload['dialogue'])} lines.", file=sys.stderr)

    api_key = load_env()
    show = load_show()
    voices = resolve_voices(show, args)
    names = {sp: show.get("hosts", {}).get(sp, {}).get("name", sp) for sp in SPEAKERS}
    present = [sp for sp in ("host", "guest", "intern") if any(l["speaker"] == sp for l in dialogue)]
    stem = path.stem if args.max_lines == 0 else f"smoke-{path.stem}"
    out_path = Path(args.out) if args.out else (AUDIO_DIR / f"{stem}.mp3")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(
        f"Rendering {len(dialogue)} lines with {args.model} ("
        + ", ".join(f"{names[sp]}={voices[sp]}" for sp in present) + ")...",
        file=sys.stderr,
    )
    t0 = time.time()
    cold_open_lines = payload.get("cold_open_lines")
    if cold_open_lines and cold_open_lines >= len(dialogue):
        cold_open_lines = None  # --max-lines cut inside the teaser
    segment, tok_in, tok_out, cold_open_ms = render_dialogue(dialogue, api_key, args.model, voices, cold_open_lines)
    cost = tok_in / 1e6 * PRICE_INPUT_PER_M + tok_out / 1e6 * PRICE_OUTPUT_PER_M
    print(
        f"  {len(segment) / 1000:.1f}s of audio in {time.time() - t0:.1f}s; tokens in={tok_in} out={tok_out}; "
        f"rough cost ${cost:.4f} (check current pricing)",
        file=sys.stderr,
    )

    print("Adding theme (if any), mastering to -16 LUFS, encoding MP3...", file=sys.stderr)
    mp3_bytes, _ = finish_episode(segment, cold_open_ms, music=not args.no_music)
    out_path.write_bytes(mp3_bytes)
    print(f"Wrote {out_path} ({len(mp3_bytes) / 1024:.0f} KB).")
    sys.exit(0)


if __name__ == "__main__":
    main()
