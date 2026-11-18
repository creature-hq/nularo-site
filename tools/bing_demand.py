#!/usr/bin/env python3
"""Daily search-volume check through the free Bing Webmaster API.

Why: the founder's rule (2026-11-18) is that every guide must have search
volume behind it. The cloud writer cannot log in to Bing, so this Action
measures demand for every keyword the writer might pick and writes it to
seo/demand.json, which PLAYBOOK step 2 reads before choosing a target.

What it checks each run (most useful first, capped at MAX_CALLS API calls):
  1. seo/demand-queue.json: keywords a writer run asked to have measured.
  2. backlog todo keywords and Google Autocomplete candidates
     (seo/keywords-latest.json) that have never been measured or were
     measured more than 30 days ago.
  3. Related keywords for the head terms in SEEDS, so new phrases with real
     volume get discovered (written to `discovered`, best first).
It also saves Bing's own query report for nularo.com (seo/bing-queries.json).

Numbers are Bing US searches over the last ~90 days, exact match. Google is
roughly 10 to 20 times Bing. 0 means under Bing's reporting floor.

Needs the BING_API_KEY secret (Bing Webmaster Tools > Settings > API access).
Without it the script exits quietly. Stdlib only.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEO = ROOT / "seo"
DEMAND = SEO / "demand.json"
QUEUE = SEO / "demand-queue.json"
QUERIES_OUT = SEO / "bing-queries.json"
API = "https://ssl.bing.com/webmaster/api.svc/json/"
SITE = "https://nularo.com/"
MAX_CALLS = 220
RECHECK_DAYS = 30
SEEDS = [
    "finch app", "bevel app", "whoop alternative", "habitica", "habit tracker app",
    "sleep tracker app", "sleep app", "virtual pet app", "tamagotchi app",
    "biological age", "sleep debt", "sleep score", "pokemon sleep", "rise app",
    "sleep cycle app", "autosleep", "athlytic", "self care app", "apple watch sleep",
]


def call(method, key, **params):
    params["apikey"] = key
    url = API + method + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "nularo-seo-action"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode()).get("d")


def load(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def main():
    key = os.environ.get("BING_API_KEY", "").strip()
    if not key:
        print("BING_API_KEY not set, skipping")
        return 0

    today = dt.date.today()
    start = (today - dt.timedelta(days=90)).isoformat()
    end = today.isoformat()
    demand = load(DEMAND, {})
    us = demand.setdefault("us_3mo", {})
    checked = demand.setdefault("checked", {})
    discovered = demand.get("discovered", {})
    calls = 0
    errors = []

    def stale(k):
        d = checked.get(k)
        return not d or (today - dt.date.fromisoformat(d)).days > RECHECK_DAYS

    queue = [k.strip().lower() for k in load(QUEUE, []) if isinstance(k, str) and k.strip()]
    backlog = [i["keyword"].lower() for i in load(SEO / "backlog.json", []) if i.get("status") == "todo"]
    kw = load(SEO / "keywords-latest.json", {})
    cands = []
    for c in kw.get("new_candidates", []):
        p = c.get("phrase") or c.get("keyword") if isinstance(c, dict) else c
        if p:
            cands.append(p.lower())
    todo = list(dict.fromkeys(queue + [k for k in backlog + cands if stale(k)]))

    for k in todo:
        if calls >= MAX_CALLS:
            break
        try:
            d = call("GetKeyword", key, q=k, country="us", language="en-US", startDate=start, endDate=end)
            calls += 1
            us[k] = int((d or {}).get("Impressions") or 0)
            checked[k] = end
        except (urllib.error.URLError, ValueError, KeyError) as e:
            calls += 1
            errors.append(f"GetKeyword {k}: {e}")
            if len(errors) > 5:
                break
        time.sleep(0.3)

    for seed in SEEDS:
        if calls >= MAX_CALLS or len(errors) > 5:
            break
        try:
            rows = call("GetRelatedKeywords", key, q=seed, country="us", language="en-US", startDate=start, endDate=end) or []
            calls += 1
            for r in rows:
                q = (r.get("Query") or "").lower()
                n = int(r.get("Impressions") or 0)
                if q and n > 0:
                    discovered[q] = max(n, discovered.get(q, 0))
                    us.setdefault(q, n)
        except (urllib.error.URLError, ValueError) as e:
            calls += 1
            errors.append(f"GetRelatedKeywords {seed}: {e}")
        time.sleep(0.3)

    try:
        rows = call("GetQueryStats", key, siteUrl=SITE) or []
        calls += 1
        agg = {}
        for r in rows:
            q = r.get("Query")
            if not q:
                continue
            a = agg.setdefault(q, {"query": q, "impressions": 0, "clicks": 0})
            a["impressions"] += int(r.get("Impressions") or 0)
            a["clicks"] += int(r.get("Clicks") or 0)
        QUERIES_OUT.write_text(json.dumps({"pulled": end, "queries": sorted(agg.values(), key=lambda x: -x["impressions"])}, indent=1) + "\n")
    except (urllib.error.URLError, ValueError) as e:
        errors.append(f"GetQueryStats: {e}")

    # Keywords measured this run leave the queue; anything not reached stays.
    QUEUE.write_text(json.dumps([k for k in queue if checked.get(k) != end], indent=1) + "\n")
    demand["us_3mo"] = dict(sorted(us.items(), key=lambda x: -x[1]))
    demand["discovered"] = dict(sorted(discovered.items(), key=lambda x: -x[1])[:300])
    demand["last_api_run"] = {"date": end, "calls": calls, "errors": errors[:6]}
    DEMAND.write_text(json.dumps(demand, indent=1, ensure_ascii=False) + "\n")
    print(f"{calls} calls, {len(us)} keywords measured, {len(discovered)} discovered, {len(errors)} errors")
    for e in errors[:6]:
        print("  ", e)
    return 1 if errors and calls <= len(errors) else 0


if __name__ == "__main__":
    sys.exit(main())
