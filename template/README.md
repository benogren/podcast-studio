# Podcast project

Created by the `podcast-studio` plugin. Drop in source material, run the `make-podcast` skill,
get an MP3.

```
show.json          cast, voices, mode, length, sign-off
SPEC/              style-guide.md, episode-types.md, personas/ (edit to change how the show sounds)
scripts/render.py  validate + render (Gemini multi-speaker TTS, mastering, optional music)
scripts/rotation.py  next episode's lead seat, spine, intern entrance, prior coverage
payloads/          drafted episodes (JSON) waiting to render
archived/          rendered payloads (used for continuity and seat rotation)
audio/             rendered MP3s (gitignored)
assets/            optional theme music
examples/          sample.json for a smoke test
```

Setup (the `podcast-setup` skill does this for you):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
brew install ffmpeg                      # or your platform's equivalent
cp .env.local.example .env.local         # then add your GEMINI_API_KEY
.venv/bin/python scripts/render.py --validate examples/sample.json
```

Cost: roughly $0.20 for a 25-minute episode at Gemini's introductory TTS rates; pricing changes,
so check https://ai.google.dev/pricing.
