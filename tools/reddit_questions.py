#!/usr/bin/env python3
"""Pull the last week of Reddit questions around Nularo's clusters.

Reddit blocks unauthenticated feeds, so this reads the free Arctic Shift
archive (arctic-shift.photon-reddit.com), which mirrors new posts. Stdlib only.
Writes seo/reddit-latest.json for the evening writer run (PLAYBOOK rule r):
  questions  question-like posts that match our topics, most-discussed first
  themes     word pairs that recur across 3+ separate question titles, with
             example titles: the "asked over and over" signal
Run: python3 tools/reddit_questions.py [--days 7]
"""
import json, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://arctic-shift.photon-reddit.com/api/posts/search"
UA = "nularo-seo-research/1.0 (github.com/creature-hq/nularo-site)"
# subreddit -> True when every post is on-topic, False when it must match TOPIC
SUBS = {
    "AppleWatch": False, "AppleWatchFitness": False, "sleep": True,
    "whoop": False, "ouraring": False, "finch": True, "nightshift": False,
    "getdisciplined": False, "selfimprovement": False, "iphone": False,
}
TOPIC = re.compile(r"sleep|hrv|heart rate|\brhr\b|readiness|recovery|vitals|health app|apple health|"
                   r"score|streak|habit|\bpet\b|tamagotchi|finch|bevel|athlytic|whoop|oura|bedtime|"
                   r"doomscroll|scroll|procrastinat|tired|nap|wake|insomnia|night shift|biological age|"
                   r"fitness age|vo2|stress|accountab|screen time|in bed|rem\b|deep sleep", re.I)
QUESTION = re.compile(r"\?|^(how|why|what|does|do|is|are|can|any|which|should|anyone|has|where|when)\b", re.I)
STOP = set("""a an the and or but of to in on for with my me i you your it is are was be do does did
this that how why what any can anyone has have just not no so at as from about there their they
does when where which should would could im i'm its it's get got am""".split())


def fetch(sub, after_ts, before_ts=None):
    q = {"subreddit": sub, "after": after_ts, "limit": 100,
         "fields": "id,title,selftext,created_utc,num_comments,score,subreddit"}
    if before_ts:
        q["before"] = before_ts
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r)
            if d.get("data") is not None:
                return d["data"]
        except Exception as e:  # noqa: BLE001 - archive is flaky; retry then skip
            print(f"  {sub}: {e}", file=sys.stderr)
        time.sleep(5 * (attempt + 1))
    return []


def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 7
    now = int(time.time())
    after = now - days * 86400
    posts, counts = [], {}
    for sub, all_on_topic in SUBS.items():
        got, before = [], None
        for _ in range(5):  # up to 500 posts per subreddit per week
            page = fetch(sub, after, before)
            if not page:
                break
            got += page
            before = min(int(p["created_utc"]) for p in page)
            if len(page) < 100:
                break
            time.sleep(5)
        counts[sub] = len(got)
        for p in got:
            title = (p.get("title") or "").strip()
            body = (p.get("selftext") or "").strip()
            if not title or title.startswith("[") or body in ("[removed]", "[deleted]"):
                continue
            if not QUESTION.search(title):
                continue
            if not all_on_topic and not TOPIC.search(title + " " + body[:300]):
                continue
            posts.append({
                "title": title,
                "subreddit": p.get("subreddit") or sub,
                "comments": p.get("num_comments") or 0,
                "score": p.get("score") or 0,
                "date": datetime.fromtimestamp(int(p["created_utc"]), timezone.utc).strftime("%Y-%m-%d"),
                "url": f"https://www.reddit.com/comments/{p.get('id')}",
                "excerpt": re.sub(r"\s+", " ", body)[:280],
            })
        time.sleep(2)

    posts.sort(key=lambda x: (x["comments"] + x["score"]), reverse=True)

    # recurring themes: word pairs shared by 3+ separate question titles
    pair_posts = defaultdict(list)
    for i, p in enumerate(posts):
        words = [w for w in re.findall(r"[a-z0-9']+", p["title"].lower()) if w not in STOP and len(w) > 2]
        seen = set()
        for a in range(len(words)):
            for b in range(a + 1, min(a + 4, len(words))):
                pair = " ".join(sorted((words[a], words[b])))
                if pair not in seen:
                    seen.add(pair)
                    pair_posts[pair].append(i)
    themes = [
        {"words": k, "posts": len(v), "examples": [posts[i]["title"] for i in v[:6]]}
        for k, v in pair_posts.items() if len(v) >= 3
    ]
    themes.sort(key=lambda t: t["posts"], reverse=True)

    out = {
        "pulled": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "window_days": days,
        "source": "Arctic Shift Reddit archive (reddit.com blocks unauthenticated reads)",
        "posts_scanned": counts,
        "themes": themes[:40],
        "questions": posts[:200],
    }
    with open("seo/reddit-latest.json", "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"scanned {sum(counts.values())} posts, kept {len(posts)} questions, {len(themes)} themes")
    if sum(counts.values()) == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
