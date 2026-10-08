---
name: podcast-setup
description: Set up a podcast project in the current folder (show config, host personas, style guide, Gemini TTS renderer, Python venv). Use when the user wants to start turning content into a podcast, says "set up podcast", "new podcast show", or when make-podcast finds no podcast/show.json.
---

# podcast-setup

Scaffolds a self-contained podcast project the user owns. Everything lands in a `podcast/`
folder in the current directory (or a path the user names), so it works inside an existing
notes vault or repo without touching it.

The starter files live in this plugin at `../../template/` relative to this skill's base
directory.

## Steps

1. **Check the target.** If `podcast/show.json` already exists, stop and offer to edit the config
   instead of overwriting. Never overwrite existing files.
2. **Copy the template:** `cp -R <plugin>/template/. podcast/` (including dotfiles such as
   `.env.local.example` and `.gitignore`). Keep `.gitkeep` files.
3. **Interview the user** (use AskUserQuestion; keep it to 2-3 short rounds, offer sensible
   defaults, and let them skip). Collect:
   - Show name and a one-line description of who it's for.
   - **Mode:** `conversation` (two friends riffing), `explainer` (one host walks the other
     through it), or `debate` (two opposing priors that steelman each other).
   - **Cast:** two host names, a line or two on each one's personality and what they argue well,
     and whether to include the third voice, an `intern` who carries the source material to the
     hosts (recommended for dense material; needs no extra setup).
   - Target episode length (default 2,000-3,500 words, about 13-23 minutes) and the sign-off line.
   - **Voices:** defaults are Sulafat (host), Algenib (guest), Zephyr (intern). Pick distinct
     voices that fit the personas; Gemini has 30 prebuilt voices
     (https://ai.google.dev/gemini-api/docs/speech-generation). Make sure the voice's gender
     matches how the host is described.
4. **Write the config:** fill `podcast/show.json` (set `intern_enabled`, names, voices, mode,
   `target_words`, `signoff`; delete the `_notes` key) and rewrite `SPEC/personas/host.md`,
   `guest.md` and (if enabled) `intern.md` from the interview. Personas describe the *voice*
   (priors, strengths, pace, humor, red lines), never invented biography.
5. **Python env.** From `podcast/`: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
   Check `ffmpeg -version`; if missing, tell the user to run `brew install ffmpeg` (or their
   platform's equivalent) rather than installing system packages yourself.
6. **API key.** Copy `.env.local.example` to `.env.local` and tell the user to paste their own
   `GEMINI_API_KEY` into it (free key at https://aistudio.google.com/apikey). **Never ask for the
   key in chat, never print it, never commit it.** `.env.local` is gitignored by the template.
7. **Verify with no spend:** `.venv/bin/python scripts/render.py --validate examples/sample.json`.
   Offer one paid smoke test once the key is in place:
   `.venv/bin/python scripts/render.py --max-lines 4 examples/sample.json` (a few cents), and ask
   the user to listen for the voices being distinct and matching the personas.
8. **Hand off:** tell them to run the `make-podcast` skill with their source material. Suggest an
   intro: a short "podcast hook" or intro track from a rights-cleared library such as Epidemic
   Sound (https://www.epidemicsound.com/music/themes/podcast/podcast-hooks/) or Envato Elements
   (https://elements.envato.com/royalty-free-music/podcast+intro+music), saved as
   `assets/theme.mp3`. Note both are subscriptions, so they should confirm their plan's license
   covers podcast distribution. It's optional; episodes render voice-only without it.
