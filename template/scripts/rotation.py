#!/usr/bin/env python3
"""Recommend the next episode's assignment from the archive, so rotation is mechanical
instead of something you have to remember.

Every episode payload should carry a `meta` object (the drafting skill writes it):

    "meta": {"type": "deep-dive", "spine": "research-debrief",
             "lead": "host", "intern_entrance": "cold-handoff"}

`lead` is the voice channel ("host" or "guest") that brought the material, opened, and
played the lead seat. `intern_entrance` is only for intern episodes. Rotation reads
archived/*.json (newest last, by filename) and show.json.

Rules it applies (see SPEC/episode-types.md):
  * lead seat alternates: the other host leads next
  * never repeat a spine used in the last 2 episodes; pick the least-recently-used spine
    from the episode type's preferred pool (never-used first)
  * intern entrance: avoid the last 3; `callback` only once a previous intern episode exists
  * prior coverage: list archived episodes matching your topic keywords

Usage:
    python scripts/rotation.py next --type deep-dive
    python scripts/rotation.py next --type single-subject --topic "age estimation,chatbot"
    python scripts/rotation.py history
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve().parent
ARCHIVE = PROJECT_ROOT / "archived"
SHOW = PROJECT_ROOT / "show.json"

SPINE_COOLDOWN = 2        # never reuse a spine used in the last N episodes
ENTRANCE_COOLDOWN = 3


def load_show():
    return json.loads(SHOW.read_text()) if SHOW.exists() else {}


def load_archive():
    eps = []
    for f in sorted(ARCHIVE.glob("*.json")):
        try:
            p = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        p["_file"] = f.name
        p["_meta"] = p.get("meta") if isinstance(p.get("meta"), dict) else {}
        eps.append(p)
    return eps


def other(lead):
    return {"host": "guest", "guest": "host"}.get(lead)


def pick_least_recent(options, used_in_order, cooldown):
    """options in menu order; used_in_order oldest->newest. Returns the option never used,
    else the least recently used, skipping the last `cooldown` entries."""
    blocked = set(used_in_order[-cooldown:]) if cooldown else set()
    candidates = [o for o in options if o not in blocked]
    if not candidates:
        return None
    last_seen = {o: -1 for o in options}
    for i, u in enumerate(used_in_order):
        if u in last_seen:
            last_seen[u] = i
    return min(candidates, key=lambda o: (last_seen[o], options.index(o)))


def cmd_history(eps, show):
    if not eps:
        print("No archived episodes yet.")
        return
    print(f"{'file':44} {'type':16} {'lead':6} {'spine':20} entrance")
    for e in eps:
        m = e["_meta"]
        print(f"{e['_file'][:44]:44} {m.get('type', '?'):16} {m.get('lead', '?'):6} "
              f"{m.get('spine', '?'):20} {m.get('intern_entrance', '')}")
    missing = sum(1 for e in eps if not e["_meta"])
    if missing:
        print(f"\n{missing} episode(s) have no `meta`; they can't inform rotation. "
              "Add one to their JSON if you want them counted.")


def cmd_next(eps, show, args):
    types = {t["id"]: t for t in show.get("episode_types", [])}
    if args.type and args.type not in types:
        print(f"Unknown type {args.type!r}. Defined: {', '.join(types) or '(none)'}", file=sys.stderr)
        sys.exit(1)
    etype = types.get(args.type, {})
    menu = show.get("spines") or []
    pool = [s for s in (etype.get("spines") or menu) if s in menu] or menu

    metas = [e["_meta"] for e in eps if e["_meta"]]
    leads = [m["lead"] for m in metas if m.get("lead") in ("host", "guest")]
    spines_used = [m["spine"] for m in metas if m.get("spine")]
    names = {sp: show.get("hosts", {}).get(sp, {}).get("name", sp) for sp in ("host", "guest")}

    print(f"Next episode{(' (' + etype.get('name', args.type) + ')') if args.type else ''}:")

    # lead seat
    if leads:
        nxt = other(leads[-1])
        print(f"  lead seat:   {nxt} ({names[nxt]}). Last episode's lead was {leads[-1]}.")
        print(f"               The other host is the challenger and gets the last word before the sign-off.")
    else:
        print("  lead seat:   no history; either host. Record it in `meta.lead` so the next episode rotates.")

    # spine
    choice = pick_least_recent(pool, spines_used, SPINE_COOLDOWN)
    recent = spines_used[-SPINE_COOLDOWN:]
    if choice:
        print(f"  spine:       {choice}")
    else:
        print("  spine:       every preferred spine was used in the last "
              f"{SPINE_COOLDOWN} episodes; pick any from the menu that was not.")
    print(f"               avoid (recent): {', '.join(recent) or 'none'}; preferred pool: {', '.join(pool)}")
    if spines_used and spines_used[-1] == "challenge-premise":
        print("               last episode was challenge-premise; never twice in a row.")

    # intern entrance
    if etype.get("intern", show.get("intern_enabled", False)):
        entrances = list(show.get("intern_entrances") or [])
        used = [m["intern_entrance"] for m in metas if m.get("intern_entrance")]
        had_intern = bool(used)
        options = [x for x in entrances if x != "callback" or had_intern]
        e = pick_least_recent(options, used, ENTRANCE_COOLDOWN)
        print(f"  intern:      enter via {e or 'any not used in the last 3'}"
              f"{'' if had_intern else ' (first intern episode: no callback yet)'}; "
              f"avoid {', '.join(used[-ENTRANCE_COOLDOWN:]) or 'none'}")
        print("               pair the optional mid-episode fact-check with the host who did NOT do it last time.")

    # coverage
    if args.topic:
        kws = [k.strip().lower() for k in args.topic.split(",") if k.strip()]
        hits = []
        for ep in eps:
            hay = " ".join([ep.get("title", ""), ep.get("description", ""), " ".join(ep.get("source_refs", []))]
                           + [l.get("text", "") for l in ep.get("dialogue", [])]).lower()
            found = [k for k in kws if k in hay]
            if found:
                hits.append((ep["_file"], found))
        if hits:
            print("  prior coverage (read these dialogues before drafting; go deeper, never replay):")
            for f, found in hits[-8:]:
                print(f"    - {f}  [{', '.join(found)}]")
        else:
            print("  prior coverage: none found for those keywords.")

    if show.get("eligibility_rules"):
        print("  eligibility: confirm before drafting:")
        for r in show["eligibility_rules"]:
            print(f"    - {r}")
    if etype.get("target_words"):
        lo, hi = etype["target_words"][:2]
        print(f"  length:      {lo}-{hi} words")
    print("\nWrite these into the payload as `meta`: "
          f'{{"type": "{args.type or ""}", "spine": "{choice or ""}", "lead": "<host|guest>"'
          + (', "intern_entrance": "<id>"' if etype.get("intern") else "") + "}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next", help="Recommend the next episode's lead, spine, entrance")
    n.add_argument("--type", help="Episode type id from show.json")
    n.add_argument("--topic", help="Comma-separated keywords to check for prior coverage")
    sub.add_parser("history", help="Show the archive's type/lead/spine history")
    args = ap.parse_args()
    show, eps = load_show(), load_archive()
    if args.cmd == "history":
        cmd_history(eps, show)
    else:
        cmd_next(eps, show, args)


if __name__ == "__main__":
    main()
