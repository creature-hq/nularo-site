#!/usr/bin/env python3
"""Daily demand signal for the guide engine, from Google Autocomplete.

Rasty's gum reads Google Keyword Planner for volumes. That needs a Google
Ads developer token; Autocomplete is the free stand-in. It only suggests
what enough people actually type, and suggestions come roughly in order of
popularity, so it answers two questions every morning:

  1. Is each backlog keyword still something people search? (demand)
  2. What new long-tail phrases are people typing around our clusters?
     (new_candidates, for the writer to add to seo/backlog.json)

Runs in GitHub Actions next to gsc_opportunities.py (the writing sandbox
cannot reach Google). Stdlib only, free, about 100 requests a day.

Writes seo/keywords-latest.json.
"""

import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG_CHECKS = 40  # lowest-priority-number todo items checked each day
SEED_SUFFIXES = ["", " app", " for", " vs", " reddit"]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def suggest(q):
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "hl": "en", "gl": "us", "q": q}
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception as e:
        print(f"autocomplete failed for {q!r}: {e}")
        return None
    finally:
        time.sleep(0.4)


def main():
    backlog = json.loads((ROOT / "seo" / "backlog.json").read_text())
    clusters = json.loads((ROOT / "guides" / "clusters.json").read_text())
    known = {norm(i["keyword"]) for i in backlog}

    todo = sorted((i for i in backlog if i.get("status") == "todo"), key=lambda i: i.get("priority", 999))
    demand = []
    for item in todo[:BACKLOG_CHECKS]:
        kw = item["keyword"]
        s = suggest(kw)
        if s is None:
            continue
        ns = [norm(x) for x in s]
        demand.append(
            {
                "keyword": kw,
                "priority": item.get("priority"),
                "exact_in_autocomplete": norm(kw) in ns,
                "rank": ns.index(norm(kw)) + 1 if norm(kw) in ns else None,
                # Google echoes a phrase only if people type it, and returns
                # more completions for phrases with more demand around them
                "suggestion_count": len(s),
                "suggestions": s[:8],
            }
        )

    candidates = {}
    for key, c in clusters.items():
        for seed in c.get("seeds", []):
            for suffix in SEED_SUFFIXES:
                s = suggest(seed + suffix)
                for rank, phrase in enumerate(s or [], 1):
                    n = norm(phrase)
                    # long-tail only: 3+ words, not already in the backlog
                    if len(n.split()) < 3 or n in known:
                        continue
                    hit = candidates.setdefault(n, {"phrase": phrase, "cluster": key, "seen": 0, "best_rank": rank})
                    hit["seen"] += 1
                    hit["best_rank"] = min(hit["best_rank"], rank)
    # seen under several seeds and near the top of the list = more demand
    ranked = sorted(candidates.values(), key=lambda c: (-c["seen"], c["best_rank"]))

    out = ROOT / "seo" / "keywords-latest.json"
    out.write_text(
        json.dumps(
            {
                "pulled": dt.date.today().isoformat(),
                "source": "Google Autocomplete (US, English)",
                "backlog_demand": demand,
                "new_candidates": ranked[:60],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    live = sum(1 for d in demand if d["exact_in_autocomplete"])
    print(f"{len(demand)} backlog keywords checked ({live} exact in autocomplete), {len(ranked)} new long-tail candidates -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
