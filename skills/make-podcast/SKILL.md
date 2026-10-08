---
name: make-podcast
description: Turn source material (files, URLs, pasted text, PDFs, notes, transcripts) into a podcast episode: draft a multi-host dialogue payload from the sources, validate it, and render an MP3 with Gemini TTS. Use when the user says "make a podcast from this", "turn this into an episode", "render an episode", or points at content to be voiced.
---

# make-podcast

Drafts an episode from the user's sources in the voice defined by their show, then renders it
to an MP3. One invocation is one episode. If `podcast/show.json` (or `show.json` in the cwd)
doesn't exist, run the `podcast-setup` skill first.

Work from the project folder (the one containing `show.json`). Use `.venv/bin/python` for scripts.

## Steps

1. **Read the show.** `show.json` (cast, mode, length, sign-off, voices), then
   `SPEC/style-guide.md` and each persona file in `SPEC/personas/`. Follow the style guide
   exactly; the renderer voices whatever you write, literally.
2. **Gather the sources.** The user may give file paths, URLs, pasted text, or a folder. Read them
   in full. Convert PDFs/DOCX/PPTX/HTML with `.venv/bin/markitdown <file>` (ephemeral; do not
   write converted copies next to originals). Fetch URLs with the web tools. If nothing was
   provided, ask what to cover. Keep an internal facts list (claim, number, quote, where from).
   **Every fact in the dialogue must come from the sources** (see "Fidelity" in the style guide).
   Flag anything the sources contradict or leave unknown instead of guessing.
3. **Check continuity.** Skim `archived/` for earlier episodes on the same material. Note the last
   episode's **spine** and **lead seat** (who opened and who played audience proxy) so you rotate
   both, and follow the style guide's continuity rules.
4. **Plan briefly, then proceed.** Pick the spine, the lead seat, the segment shape (two speakers
   per segment if the intern is enabled), and a target length within `target_words`. Tell the
   user the plan in 3-5 lines; if they have not said "just do it", pause for a yes or edits
   before drafting a long script.
5. **Draft the payload** at `payloads/YYYY-MM-DD-HHMM-slug.json` in the shape the style guide's
   "Payload" section shows (`title`, `description`, `cold_open_lines`, `dialogue`,
   `source_refs`). Write TTS-safe text (spell out numbers, money, scores). Then run the style
   guide's anti-patterns checklist against your own draft and fix what fails.
6. **Validate (free):** `.venv/bin/python scripts/render.py --validate payloads/<file>.json`.
   Errors block rendering; warnings are style lint. Fix errors and address warnings that point
   to real problems (uniform line lengths, hostile TTS tokens, long runs from one speaker).
7. **Render (paid, a few cents to ~$0.25):** tell the user what it will cost and wait for a yes
   the first time. Run a smoke test first: `... scripts/render.py --max-lines 6 payloads/<file>.json`
   (writes `audio/smoke-*.mp3`; confirm the voices before the full run). Then
   `... scripts/render.py payloads/<file>.json` writes `audio/<file>.mp3`. Surface cost and
   output path. If `GEMINI_API_KEY` is missing, send the user to `.env.local`; never request or
   print the key.
8. **Archive and report.** Move the rendered payload to `archived/`. Report the MP3 path, duration,
   the spine and lead seat used (so the next episode rotates), and any facts the sources left
   unknown. Do not publish or upload anywhere unless the user asks.

## Notes

- Exit codes from `render.py`: 1 validation, 2 API client error, 3 API server/rate limit,
  4 config/dependency (missing key, ffmpeg), 5 audio error.
- Never edit files in the user's source folders. Never commit `.env.local` or MP3s.
- Voices live in `show.json`; per-run overrides are `--host-voice`, `--guest-voice`, `--intern-voice`.
