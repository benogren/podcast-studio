# podcast-studio

A Claude Code plugin that turns any source material (articles, notes, PDFs, transcripts, a folder
of research) into a polished multi-host podcast episode.

**How it works:** Claude reads your sources and drafts a dialogue in the voices you define (two
hosts, plus an optional "intern" who carries the facts), validates it, and renders an MP3 with
Gemini's multi-speaker text-to-speech, wrapped in optional theme music and loudness-mastered.
Everything runs on your machine; the only service called is the Gemini API with your own key.

- Style engine: fast, specific, opinionated conversation, with rules for rhythm, interjections,
  numbers, humor, a fixed cold-open/close skeleton, and a **fidelity rule**: every fact must trace
  to your sources.
- Three modes: `conversation`, `explainer`, `debate` (hosts steelman each other).
- Optional third voice (the intern) who simplifies the material; segments are written two voices at
  a time to fit Gemini's two-speaker-per-request limit.
- Free validation and style lint before you spend anything on audio.

## Install

```
/plugin marketplace add benogren/podcast-studio
/plugin install podcast-studio@podcast-studio
```

Then, in the folder where you want the show to live:

1. Run the **podcast-setup** skill. It scaffolds `podcast/`, interviews you about the show, writes
   the persona files, creates the Python environment, and checks `ffmpeg`.
2. Add your own `GEMINI_API_KEY` to `podcast/.env.local` (free key:
   https://aistudio.google.com/apikey).
3. Point the **make-podcast** skill at your material: "make a podcast from `notes/q3-research.md`".

## Requirements

- Claude Code
- Python 3.9+ and `ffmpeg`
- A Gemini API key (a 25-minute episode costs roughly twenty cents at introductory rates)

## Notes

- You own the generated `podcast/` folder; edit the style guide and personas freely.
- Theme music is optional and not included. Grab a short intro from a rights-cleared library such as
  [Epidemic Sound](https://www.epidemicsound.com/music/themes/podcast/podcast-hooks/) or
  [Envato Elements](https://elements.envato.com/royalty-free-music/podcast+intro+music), confirm your
  plan's license covers podcast distribution, and save it as `podcast/assets/theme.mp3`.
- The hosts are synthetic voices. If you publish, disclose that.
- The dialogue style is modeled on conversational business podcasts but contains no transcripts or
  copyrighted text.

MIT licensed.
