#!/usr/bin/env python3
"""Find the queries Google already shows nularo.com for, but nobody clicks.

This is the core of the daily loop (Rasty's: "your site was showed 16,000
times for this keyword, but no clicks because you are like number 50").
A query with impressions and a deep position (or a low click-through rate)
is a guide Google is half-willing to rank. Writing a page aimed squarely at
it is the cheapest win there is.

Stdlib only. Credentials come from the environment, never from the repo
(the repo is public):

  GSC_CLIENT_ID, GSC_CLIENT_SECRET, GSC_REFRESH_TOKEN
      An OAuth refresh token with the webmasters.readonly scope, for the
      Google account that owns the nularo.com property.
  GSC_SITE  (optional) defaults to https://nularo.com/

Runs daily in GitHub Actions (.github/workflows/search-console.yml), since
the guide-writing sandbox cannot reach Google.

Writes seo/gsc-latest.json:
  totals         site-wide impressions, clicks, query count for the range
  opportunities  queries worth a new guide or a title rewrite
  pages          every page with impressions, busiest first (link FROM these)
  queries        every query Google showed us for, with the page it showed
  index          Google's index verdict for each guide in the sitemap

Exits 0 with a note when credentials are missing, so the daily agent falls
back to the keyword backlog instead of failing.
"""

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = os.environ.get("GSC_SITE") or "https://nularo.com/"
# A brand-new site sees single-digit impressions for weeks. Five is enough
# to tell the writer Google is testing us for a query.
MIN_IMPRESSIONS = 5


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


def post(access, url, body):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def resubmit_sitemap(access):
    """Resubmit the sitemap so Google rereads it the morning a guide ships.
    Google dropped the anonymous sitemap ping in 2023; this is the API way."""
    site = urllib.parse.quote(SITE, safe="")
    feed = urllib.parse.quote(SITE.rstrip("/") + "/sitemap.xml", safe="")
    req = urllib.request.Request(
        f"https://www.googleapis.com/webmasters/v3/sites/{site}/sitemaps/{feed}",
        method="PUT",
        headers={"Authorization": f"Bearer {access}"},
    )
    try:
        urllib.request.urlopen(req).read()
        print("sitemap resubmitted")
    except urllib.error.HTTPError as e:
        print(f"sitemap resubmit failed: {e.code}")


def query(access, body):
    url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(SITE, safe='')}/searchAnalytics/query"
    return post(access, url, body).get("rows", [])


def guide_urls():
    """Guide URLs from the live sitemap (what Google was told about)."""
    try:
        with urllib.request.urlopen(SITE.rstrip("/") + "/sitemap.xml", timeout=20) as r:
            xml = r.read().decode()
    except Exception as e:
        print(f"could not read sitemap: {e}")
        return []
    return [u for u in re.findall(r"<loc>([^<]+)</loc>", xml) if "/guides/" in u]


def inspect(access, url):
    try:
        r = post(
            access,
            "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            {"inspectionUrl": url, "siteUrl": SITE},
        )
        i = r["inspectionResult"]["indexStatusResult"]
        return {"url": url, "verdict": i.get("verdict"), "coverage": i.get("coverageState"), "last_crawl": i.get("lastCrawlTime")}
    except Exception as e:
        return {"url": url, "verdict": "ERROR", "coverage": str(e)[:120]}


def main():
    if not all(os.environ.get(k) for k in ("GSC_CLIENT_ID", "GSC_CLIENT_SECRET", "GSC_REFRESH_TOKEN")):
        print("no Search Console credentials in the environment; use seo/backlog.json instead")
        return
    end = dt.date.today() - dt.timedelta(days=2)  # GSC data lags ~2 days
    start = end - dt.timedelta(days=28)
    access = token()
    resubmit_sitemap(access)
    window = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dataState": "all"}

    rows = query(access, {**window, "dimensions": ["query", "page"], "rowLimit": 5000})
    queries, opps = [], []
    for r in rows:
        q, page = r["keys"]
        imp, clicks, pos, ctr = r["impressions"], r["clicks"], r["position"], r["ctr"]
        queries.append({"query": q, "page": page, "impressions": imp, "clicks": clicks, "position": round(pos, 1)})
        if imp < MIN_IMPRESSIONS:
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
    queries.sort(key=lambda o: o["impressions"], reverse=True)

    pages = [
        {"page": r["keys"][0], "impressions": r["impressions"], "clicks": r["clicks"], "position": round(r["position"], 1)}
        for r in query(access, {**window, "dimensions": ["page"], "rowLimit": 1000})
    ]
    pages.sort(key=lambda p: (p["clicks"], p["impressions"]), reverse=True)

    index = [inspect(access, u) for u in guide_urls()[:60]]

    out = ROOT / "seo" / "gsc-latest.json"
    out.write_text(
        json.dumps(
            {
                "pulled": dt.date.today().isoformat(),
                "range": [start.isoformat(), end.isoformat()],
                "totals": {
                    "impressions": sum(p["impressions"] for p in pages),
                    "clicks": sum(p["clicks"] for p in pages),
                    "queries": len({q["query"] for q in queries}),
                },
                "opportunities": opps[:100],
                "pages": pages[:100],
                "queries": queries[:300],
                "index": index,
            },
            indent=2,
        )
        + "\n"
    )
    for o in opps[:25]:
        print(f'{o["impressions"]:>6} imp  pos {o["position"]:>5}  ctr {o["ctr"]:.1%}  {o["query"]}  ->  {o["page"]}  [{o["action"]}]')
    indexed = sum(1 for i in index if i["verdict"] == "PASS")
    print(f"{len(opps)} opportunities, {len(queries)} query rows, {len(pages)} pages, {indexed}/{len(index)} guides indexed -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
