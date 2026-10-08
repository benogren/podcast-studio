# Dialogue Style Guide

How to write the `dialogue` array of an episode payload so it sounds like two (or three)
people talking, not a script being read. The renderer voices whatever you write, literally,
so every rule here is about what ends up on the page.

Edit this file to taste. The drafting skill reads it before every episode.

## The cast

The cast comes from `show.json` and the persona files in `SPEC/personas/`.

- **`host`** and **`guest`** are the two co-hosts. They are equals who share the floor.
- **`intern`** (optional, `intern_enabled` in `show.json`) is a third voice who has read the
  source material and carries it to the hosts. A guest, not a co-host.
- `speaker` is a **fixed voice channel**, never a name. Names are spoken in the text,
  vocatively at hand-offs and teases ("Sam, have you heard of this?"), not in every line, and
  nobody introduces themselves.

Persona consistency matters more than any other rule: a host who sounds like someone else for a
few lines is the fastest way to sound synthetic. Read the persona files first.

## Fidelity: the sources are the only facts

Every number, date, name, quote and claim in the dialogue must trace to the source material you
were given. The hosts may have opinions, reactions and analogies; they may not invent facts.

- Hedge peripheral details ("I think it was March") so the load-bearing numbers, stated exactly,
  land harder. Never hedge a number the episode's argument depends on.
- If the sources don't say, say so on air ("the article doesn't give a number").
- Attribute contested claims to whoever made them. Quote casually and specifically ("the report
  puts it at four point two million a year").
- Reuse no copyrighted text beyond a short quoted phrase; paraphrase and react.

## The authenticity line

The hosts are synthetic. They may speak in first person about the **research process**, because
it's true: "I fell down a rabbit hole on this," "I reread the whole thing," "this number genuinely
bothered me." They may **not** claim invented biography or fieldwork: no "when I ran my company,"
no "I called them this morning," no fabricated friends or war stories. Strong feelings about the
material (**reaction honesty**) carry the same energy without the lie.

## Episode skeleton

1. **Cold open (2-4 lines, hosts only).** The episode's best moments pulled forward: a surprising
   number, a zinger, a "wait, that's what it actually says?" These may repeat verbatim later.
   **Set `cold_open_lines` in the payload to the number of teaser lines**; the renderer plays the
   intro theme right after them, so the line that follows should work as the first line after a
   theme song.
2. **The restart and hook.** A line that forces the other voice to respond: a knowledge check
   ("Have you actually read what's in this? Because it's not what the headline says"), a game
   setup, a challenge premise, or a stakes hook. **Never open on a thesis monologue, never
   "Welcome to the show."**
3. **Segments.** See "Mechanics." Enumerate out loud when it's a list ("Alright, number three").
4. **The close (fixed sequence):** one sincere zoom-out beat, then a deflating joke or callback to
   the cold open, then the sign-off from `show.json` (`signoff`). If the episode opened on a
   challenge premise, adjudicate it. Never end on a mic-drop thesis, a synthesis monologue, or
   "thanks for listening."

## Modes (`mode` in `show.json`)

- **conversation:** two friends riffing on the material; one brought it and the other reacts fresh.
- **explainer:** one host walks the other through it, with the other asking the smart questions.
- **debate:** two hosts with opposing priors. Rules: state the facts first, **steelman before you
  rebut** (state the other side's strongest point in a form they'd accept), disagree about values
  and tradeoffs rather than facts, no manufactured symmetry when the evidence is lopsided, attack
  the idea and never the person, and close on the **real crux** of the disagreement.

All three share **asymmetric prep**: one voice arrives with something prepared (a list, a
document, a game) the other hasn't seen. Don't make everyone equally informed; that's a synthetic tell.

## The intern format (when `intern_enabled`)

Gemini voices **at most two speakers per request**, so **every segment has exactly two speakers
talking.** The standard shape:

1. **Open: host and guest.** Cold open, hook, bring the intern in.
2. **Intern and the lead host:** the explanation. The lead host is the audience proxy.
3. **Intern and the other host:** the challenge. Receipts, counterexamples, the sources' open questions.
4. *(Optional)* **Hosts only:** the argument or reaction.
5. **Close: host and guest**, after the intern has gone: sincere beat, joke or callback, sign-off.

Make every hand-off a clean line ("Sam, she's all yours"). Never let a third voice drop in with a
one-liner mid-segment; the renderer splits there and it sounds stitched.

**Rotate the lead.** `scripts/rotation.py next` names who leads (who opens, who brings the intern
in, who plays audience proxy); it alternates every episode. See `SPEC/episode-types.md`.

**Vary the intern's entrance**, and never frame the episode as an experiment ("we're trying
something new"): a cold hand-off, a knowledge check through her, a callback to last time, a
mid-argument "okay, we need the intern," or an assignment reveal ("I sent Riley one question and
she came back with forty pages"). She uses the hosts' names at hand-offs and never introduces herself.

**The simplifier test:** every mechanism gets the one-sentence version, then a plain analogy or
concrete example, then the jargon spelled out. If a smart newcomer couldn't follow it the first
time through, simplify again.

## Spines: the menu

The skeleton is fixed; the **spine** (the game inside it) varies. `scripts/rotation.py next`
recommends one (see `SPEC/episode-types.md`); never reuse a spine from the last two episodes.
Spine ids, in order, match `show.json`: reaction-relay, document-teardown, judged-countdown,
rug-pull, prove-me-wrong, masterclass, research-debrief, case-study-relay, challenge-premise.

1. **Reaction relay.** One voice consumed the source and relays it one "thing" at a time, sorted
   into labeled buckets; the other reacts fresh.
2. **Document teardown.** "Two idiots and a document." Chain through the components with Socratic
   role-play and guess-the-number beats.
3. **Judged countdown.** A bit becomes a rulebook ("good idea or bad idea?"); each item gets a
   binary verdict.
4. **Rug-pull myth-busting.** Build the legend sincerely, then "everything I just told you is a
   lie," and generalize into criteria for what's real.
5. **Prove-me-wrong workshop.** The skeptic is converted by a live demonstration on a concrete
   example, not by argument.
6. **Masterclass.** A time-bound promise, a pre-announced curriculum, principle then worked
   example then handoff.
7. **Research debrief.** "I spent two days inside this and wrote down five things." List them all
   up front, then hand over navigation: "Which one do you want first?"
8. **Case-study relay.** Trade parallel cases and let a taxonomy emerge from accumulation.
9. **Challenge premise.** Doubt stated in line one, close settles the bet. Never twice in a row.

## Rhythm: monologue plus burst

The most detectable synthetic tell is **uniform alternation**: speakers trading same-length lines.
Real rhythm is lopsided.

- **Lead beats:** the owner of a point holds the floor for 150-400 words, 2-4 consecutive lines
  each under ~400 characters, with the other voice interjecting every ~100-150 words.
- **Bursts:** runs of 5-10 rapid exchanges under ~15 words: reactions, number demands, verdicts.
- Line length should be *visibly varied* in the JSON: a 60-word setup beside a 6-word echo beside
  a 200-word walkthrough. If every line is 40-50 words, rewrite.
- Cap any speaker at 4 consecutive lines, then force an interjection.

## The interjection toolkit

**Never agree by repeating the other voice's words back.** Agreement is a short token plus a move:
"That's fair, and it gets worse." One-word lines standing alone ("Right." "Yeah.") read as hollow;
give them a tail. Short lines (3-8 words) should do a job:

- **Agreement plus move** ("Yep, that's the one. Keep going.")
- **Echo-completion:** finish or *upgrade* the other's sentence, never replay it
- **Restatement check** ("So the money's already banked. Is that right?")
- **Blunt number demand** ("How much?" "How many people?")
- **Operationalizing question** ("And who actually does that part?")
- **Verdict** ("Good idea. Next.")
- **Continue-prompt** ("Okay, so what happened?")

## Mechanics

- **Open a segment with a knowledge check.** The owner tests the other voice ("Have you heard of
  X?") and is *delighted* by a no: "Good, because the headline is wrong. Here's what it says."
- **Read the artifact aloud.** Don't summarize the source; quote a line and react to it.
- **Numbers: extract bluntly, compute publicly.** Blunt extraction ("Say the number."), public
  math ("call it four million, across sixty-four counties, that's sixty-five grand each"),
  guess-the-number games, and translation to human scale ("about ninety dollars a year per household").
- **Story anatomy:** a named actor, what they did, the stake, and a coined lesson. Reenact quoted
  dialogue ("he goes," "she's like") instead of summarizing.
- **Pushback is concede-then-carve.** Label the fight, concede the true part, carve the rest, cite
  a counterexample instead of an attitude, and resolve within ~4 exchanges (absorbed, narrowed, or
  left as a named honest disagreement).
- **Register: energy, then one sincere sidebar, then puncture it.** Budget 1-2 sincere stretches:
  enter via a flag ("Can we be real for a second?"), slow down, no jokes; the other voice matches
  the sincerity, and the deflating beat comes after as the exit.
- **Humor:** escalating each other's bits, affectionate roasting of each other (never of the
  subjects), one fake-sponsor gag at most.
- **Spoken English, not written English.** Contractions, fragments, "he goes." Read each line
  aloud in your head; if it'd be awkward at a dinner table, rewrite. Coin names for patterns.
  Spell out acronyms on first use. Banned generic tells: "That's a great point," "Absolutely,"
  "I completely agree," "To your point."

## TTS rules: write tokens the way they're spoken

The renderer reads text literally. `scripts/render.py --validate` warns about these.

- **Money:** "four point two million dollars," never "$4.2M".
- **Percent:** "twelve percent," never "12%".
- **Multiples and quarters:** "three times," "first quarter," never "3x" or "Q1".
- **Scores and ranges:** "seven to four," never "7-4".
- **Years:** plain digits are fine ("in 1995"); the renderer converts them to spoken form.
- **No** stage directions (`[laughs]`), no inline vocal tags, no markdown, no URLs, no bullets.
- Anything ambiguous: read it aloud and write what you'd say.

## Continuity

Before drafting, check `archived/` for prior coverage of the same material or topic. If an earlier
episode touched it, read its dialogue first.

1. **Go deeper, not louder.** The follow-up earns its existence with what's new.
2. **Never reuse** the earlier episode's analogies, coined phrases, jokes, or phrasing.
3. **Use memory callbacks instead of repeats:** one line ("we got this about forty percent right
   last time"), then straight into the new material.

## Pace and length

- **Length is a budget, not a quota.** At ~150 words per minute, 4,500 words is about 30 minutes.
  Padding (recaps of settled points, re-argued fights, manufactured tangents) is a worse tell than
  brevity: cover the material, then close.
- A single source or short piece: ~2,000-3,500 words. A rich batch or deep dive: up to ~4,500.
- Roughly 60-130 lines at full length. Line-length variance matters more than line count.
- Most lines under ~400 characters (the hard limit is 2,000; over ~1,000 sounds like a lecture).

## Payload

```json
{
  "title": "Episode title (1-200 chars)",
  "description": "One or two sentences for the show notes (1-500 chars)",
  "cold_open_lines": 3,
  "dialogue": [
    { "speaker": "host", "text": "..." },
    { "speaker": "guest", "text": "..." },
    { "speaker": "intern", "text": "..." }
  ],
  "source_refs": ["article-one.md", "https://example.com/report"]
}
```

Name the file `payloads/YYYY-MM-DD-HHMM-slug.json`. `speaker` is one of `host`, `guest`, `intern`.

## Anti-patterns checklist (scan before saving)

- [ ] Uniform alternation (every line 40-50 words, strict trading)
- [ ] A fact, number, or quote that isn't in the sources
- [ ] Persona drift, or the lead seat changing hands mid-episode
- [ ] Same spine as either of the last two episodes
- [ ] Missing cold open, a missing or miscounted `cold_open_lines`, or an opening thesis monologue
- [ ] A close that's a mic-drop or synthesis instead of sincere beat, joke or callback, sign-off
- [ ] Parrot-echo agreement; one-word interjections standing alone
- [ ] TTS-hostile notation ("$4M", "12%", "3x", "7-4")
- [ ] Three voices in one segment, or the intern taking the sincere beat or the sign-off
- [ ] The intern introduced as a novelty, or explaining with jargon first
- [ ] Padding to hit a length target; replaying beats from a prior episode
- [ ] Invented biography or fieldwork for any voice
- [ ] Stage directions, URLs, markdown, names in the `speaker` field
- [ ] Every fact stated with equal precision (no hedging anywhere)
- [ ] Anecdotes told in summary with no reenacted dialogue
- [ ] Disagreement that runs past ~4 exchanges or turns personal

## Worked micro-example

Everything in it is invented for illustration; do not copy it, and write fresh from the actual sources. Note the shape: knowledge-check opener,
consecutive lead lines, echo-completion, public math, a coined name, concede-then-carve.

```json
{ "speaker": "host", "text": "Alright, next one. Have you heard of a company called Ledgerly? Not the accounting thing. The company." },
{ "speaker": "guest", "text": "That rings a bell and I can't place it. What is it?" },
{ "speaker": "host", "text": "I love that you don't know this, because I didn't either until Tuesday. They make the invisible code that moves money between small banks and the apps you use. Every app in this report runs through them. And last week the biggest of those apps bought them for three hundred million dollars." },
{ "speaker": "guest", "text": "Wait, wait. Including the rival apps' payments?" },
{ "speaker": "host", "text": "All of them. As of last week, the pipes your competitors use are owned by you." },
{ "speaker": "guest", "text": "That's not an acquisition, that's buying the umpire." },
{ "speaker": "host", "text": "Buying the umpire. I'm stealing that. And do the math: call it four hundred billion dollars flowing through those pipes. Three hundred million to own the tollbooth is a rounding error." },
{ "speaker": "guest", "text": "Friendly fight, though. I think the umpire thing cuts the other way. I agree it's a cheap seat in the middle of everything. I just don't think the rivals stay on a competitor's pipes for six months. So what did they actually buy?" },
{ "speaker": "host", "text": "A two-year head start while everyone else rebuilds the plumbing. That's the whole bet." }
```
