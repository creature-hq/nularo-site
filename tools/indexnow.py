#!/usr/bin/env python3
"""Tell Bing (and every other IndexNow engine: Yandex, Naver, Seznam) that
pages changed. Bing's index also feeds ChatGPT search, Copilot, DuckDuckGo
and Yahoo. Google does not use IndexNow; it reads the sitemap, which
gsc_opportunities.py resubmits every morning.

The key file <KEY>.txt at the site root proves we own nularo.com.

Run:  python3 tools/indexnow.py --all          every URL in sitemap.xml
      python3 tools/indexnow.py --since <rev>  pages changed since a git revision
"""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "nularo.com"
SITE = f"https://{HOST}"
KEY = "48a5ff6ece4cc0a3761cf976305cb0a0"


def all_urls():
    return re.findall(r"<loc>([^<]+)</loc>", (ROOT / "sitemap.xml").read_text())


def changed_urls(rev):
    out = subprocess.run(
        ["git", "diff", "--name-only", rev, "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    urls = []
    for f in out:
        if f == "index.html":
            urls.append(f"{SITE}/")
        elif re.fullmatch(r"guides/(?:[\w-]+/)?index\.html", f):
            urls.append(f"{SITE}/{f[: -len('index.html')]}")
        elif re.fullmatch(r"[\w-]+\.html", f) and f not in ("404.html",) and not f.startswith("google"):
            urls.append(f"{SITE}/{f}")
    return sorted(set(urls))


def main():
    if "--all" in sys.argv:
        urls = all_urls()
    elif "--since" in sys.argv:
        urls = changed_urls(sys.argv[sys.argv.index("--since") + 1])
    else:
        sys.exit(__doc__)
    if not urls:
        print("nothing changed, nothing to ping")
        return
    body = {"host": HOST, "key": KEY, "keyLocation": f"{SITE}/{KEY}.txt", "urlList": urls}
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow {r.status}: pinged {len(urls)} URLs")
    except urllib.error.HTTPError as e:
        # 202 = accepted, key not yet verified; 403/422 = key file not live yet
        sys.exit(f"IndexNow {e.code}: {e.read().decode()[:300]}")
    for u in urls:
        print(" ", u)


if __name__ == "__main__":
    main()
