# Episode types and rotation

A show usually needs more than one *kind* of episode, and each kind needs its own trigger,
cast, length and rules. Then, within the show, a handful of things have to **rotate** or the
show starts to sound formulaic. This file defines both. The presets live in `show.json`
(`episode_types`); edit, rename or delete them to fit your show.

## The three presets

| Type | When you make it | Cast | Length | Favored spines |
| --- | --- | --- | --- | --- |
| **Digest** | A batch of new material arrives (a day or week of newsletters, articles, saved links). Recurring. | Two hosts only | 3,000-4,500 words | reaction-relay, judged-countdown, research-debrief, case-study-relay |
| **Deep dive** | A subject has accumulated enough material to cover properly. Triggered, not scheduled. | Two hosts + intern | 2,000-4,500 words | document-teardown, research-debrief, rug-pull, masterclass, prove-me-wrong |
| **Single-subject** | One primary source (report, paper, bill, filing, long article) deserves its own episode. | Two hosts + intern, `debate` mode | 2,000-3,500 words | document-teardown, research-debrief, prove-me-wrong, challenge-premise |

### Digest

The workhorse. You hand it a pile of new things and get one episode that groups them into 3-6
themed stories. **One host "brought everything" and leads every segment; the other is the
audience proxy**, which gives the episode its asymmetric-prep energy. No intern: a digest
moves too fast for a fact-carrier. Skip anything that is only a passing mention; cover what has
a named actor, a number and a stake. Spines that suit it: relaying the pile in labeled buckets,
running a judged countdown, or a research debrief ("I spent the morning inside these and wrote
down five things").

### Deep dive

Where the intern earns her place. Use it when the material on a subject has built up and the
earlier digests only gave the headline. Shape: open (hosts) -> intern with the lead host (the
explanation, hosts as audience proxy) -> intern with the other host (the challenge, receipts
and open questions) -> close (hosts). **Go deeper, not louder:** if a digest already covered the
story, the deep dive earns its slot with what the accumulated material adds (history, mechanism,
second-order numbers, the counterargument, the pattern across sources), and uses a one-line
memory callback instead of replaying beats.

### Single-subject

One document, taken seriously. In `debate` mode the intern carries the source's facts and takes
no side; the hosts argue from them, steelman before they rebut, and close on the real crux.
Use `conversation` or `explainer` mode if the material isn't contested.

## Triggers and eligibility

Types are **not rotated**; they are triggered by what you have. What you *choose to cover* is
yours: put your own gate in `show.json` under `eligibility_rules` (for example, "no dedicated
episodes about a specific person or company", or "only subjects with at least three sources").
`scripts/rotation.py next` prints those rules every time so the drafting step cannot skip them.

**The queue pattern:** drafting and rendering are separate. Draft payloads into `payloads/` as
material arrives (that folder is your queue), review them, and render when you want audio.
Rendered payloads move to `archived/`, and the archive is what rotation reads.

## What rotates, and how

Four things rotate. `scripts/rotation.py` computes all of them from `archived/*.json`.

1. **Lead seat.** The host who brought the material, opened, and played the lead seat alternates
   every episode: if `host` led last time, `guest` leads next. The other host is the challenger
   and gets the last word before the sign-off. Across a run, neither persona should lead more
   than the other. *Voices never swap*: each host keeps one recognizable voice; only the editorial
   seat rotates.
2. **Spine.** The game inside the fixed skeleton (see the style guide's spine menu). Never reuse a
   spine from the last two episodes; prefer the least recently used one from the episode type's
   pool. `challenge-premise` never runs twice in a row.
3. **Intern entrance** (intern episodes only). Vary how she is brought in: `cold-handoff`,
   `knowledge-check`, `callback`, `mid-argument-summon`, `assignment-reveal`. Avoid the last three;
   `callback` only once a previous intern episode exists. Alternate which host she pairs with for
   the optional fact-check.
4. **Prior coverage.** Before drafting, `rotation.py next --topic "kw1,kw2"` lists archived episodes
   that already touched the subject. Read their dialogue, then follow the style guide's
   continuity rules.

## Recording it: the `meta` block

Rotation only works if each episode says what it was. Add this to every payload (the
`make-podcast` skill does it for you):

```json
"meta": {
  "type": "deep-dive",
  "spine": "research-debrief",
  "lead": "host",
  "intern_entrance": "cold-handoff"
}
```

`lead` is `host` or `guest` (the voice channel, not a name). `intern_entrance` is only for
intern episodes. `python scripts/rotation.py history` shows the table so you can see the pattern.

## Using it

```bash
python scripts/rotation.py next --type deep-dive --topic "interest rates,fed"
python scripts/rotation.py history
```
