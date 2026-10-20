#!/usr/bin/env python3
"""Find the queries Google already shows nularo.com for, but nobody clicks.

This is the core of the daily loop: a query with impressions and a deep
position (or a low click-through rate) is a guide Google is half-willing
to rank. Writing a page aimed squarely at it is the cheapest win there is.

Stdlib only. Credentials come from the environment, never from the repo
(the repo is public):

  GSC_CLIENT_ID, GSC_CLIENT_SECRET, GSC_REFRESH_TOKEN
      An OAuth refresh token with the webmasters.readonly scope, for the
      Google account that owns the nularo.com property.
  GSC_SITE  (optional) defaults to https://nularo.com/

Runs daily in GitHub Actions (.github/workflows/search-console.yml), since
the guide-writing sandbox cannot reach Google.

Writes seo/gsc-latest.json and prints the top opportunities. Exits 0 with
a note when credentials are missing, so the daily agent falls back to the
keyword backlog instead of failing.
"""

import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = os.environ.get("GSC_SITE") or "https://nularo.com/"


def token():
    data = urllib.parse.urlencode(
        {
            "client_id": os.environ["GSC_CLIENT_ID"],
            "client_secret": os.environ["GSC_CLIENT_SECRET"],
            "refresh_token": os.environ["GSC_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }
    ).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        return json.load(r)["access_token"]


def query(access, body):
    url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(SITE, safe='')}/searchAnalytics/query"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r).get("rows", [])


def main():
    if not all(os.environ.get(k) for k in ("GSC_CLIENT_ID", "GSC_CLIENT_SECRET", "GSC_REFRESH_TOKEN")):
        print("no Search Console credentials in the environment; use seo/backlog.json instead")
        return
    end = dt.date.today() - dt.timedelta(days=2)  # GSC data lags ~2 days
    start = end - dt.timedelta(days=28)
    access = token()
    rows = query(
        access,
        {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query", "page"],
            "rowLimit": 5000,
        },
    )
    opps = []
    for r in rows:
        q, page = r["keys"]
        imp, clicks, pos, ctr = r["impressions"], r["clicks"], r["position"], r["ctr"]
        if imp < 20:
            continue
        # deep position = Google is testing us; low CTR on page 1 = the title is wrong
        if pos > 8 or ctr < 0.02:
            opps.append(
                {
                    "query": q,
                    "page": page,
                    "impressions": imp,
                    "clicks": clicks,
                    "ctr": round(ctr, 4),
                    "position": round(pos, 1),
                    "action": "new guide" if pos > 15 else "rewrite title/description or deepen the section",
                }
            )
    opps.sort(key=lambda o: o["impressions"], reverse=True)
    out = ROOT / "seo" / "gsc-latest.json"
    out.write_text(json.dumps({"pulled": dt.date.today().isoformat(), "range": [start.isoformat(), end.isoformat()], "opportunities": opps[:100]}, indent=2))
    for o in opps[:25]:
        print(f'{o["impressions"]:>6} imp  pos {o["position"]:>5}  ctr {o["ctr"]:.1%}  {o["query"]}  ->  {o["page"]}  [{o["action"]}]')
    print(f"{len(opps)} opportunities written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
