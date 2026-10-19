#!/usr/bin/env python3
"""Build the Nularo guides.

Stdlib only, on purpose: the daily agent runs this in a fresh cloud
checkout with nothing installed.

Source:  guides/src/<slug>.html  = a JSON header in an HTML comment,
         then the article body as plain HTML.
Output:  guides/<slug>/index.html, guides/index.html, sitemap.xml,
         robots.txt, llms.txt.

Optional meta keys: seo_title (title tag if it should differ from the H1),
tldr (the ~80 word direct answer, shown in a box under the H1), howto (list
of step strings, emits HowTo schema), faq (list of {q, a}), related (slugs),
cta (which CTA_COPY variant the end card uses), keyword (target query).

Shortcodes inside a body:
  <!-- cta -->            inline App Store card (default copy). Use at most one,
                          late in the article, after the free/native answer.
  <!-- cta:age -->        inline card, Creature Age copy
  <!-- cta:sleep -->      inline card, sleep copy
  <!-- cta:pet -->        inline card, virtual pet copy
  <!-- cta:habits -->     inline card, habits copy
  <!-- shot:NAME -->      a real app screenshot from img/app/NAME.webp

Run:  python3 tools/build.py          (build)
      python3 tools/build.py --check  (build, then fail on broken links / em dashes)
"""

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "guides" / "src"
OUT = ROOT / "guides"
SITE = "https://nularo.com"
APP_ID = "6792171696"
# App Store Connect provider token. When set, every App Store link carries
# ct=<guide slug> so App Analytics shows downloads per guide. Find it in
# App Store Connect > Apps > Nularo > App Analytics > Campaigns > Generate link.
PROVIDER_TOKEN = ""

CLUSTERS = json.loads((OUT / "clusters.json").read_text())

SHOTS = {
    "age-tab": "Nularo's Age tab: a Creature Age of 27.9 against a real age of 22, with the age history graph",
    "overview": "Nularo's Overview tab: last night's sleep, sleep debt, stress, energy, resting heart rate and HRV",
    "creature": "Nularo's creature on the home screen, judging last night",
    "today": "Nularo's Today screen: last night's sleep, steps and resting heart rate, the Bedtime Pledge and Creature Age",
    "milestones": "Nularo's Milestones tab: weekly goals and what the app noticed about bedtime, sleep, steps and movement",
    "onboarding-creature-age": "Nularo onboarding screen explaining Creature Age",
    "connect-apple-health": "Nularo asking for read-only Apple Health access: sleep, steps, resting heart rate and HRV",
}

CTA_COPY = {
    "default": (
        "Want the data to actually mean something?",
        "Nularo reads your Apple Health every night and turns it into a creature that reacts to how you really slept and moved. Nothing to log.",
    ),
    "age": (
        "See how old your habits are making you",
        "Nularo turns your Apple Health sleep and movement into a Creature Age, with a breakdown of which habit added the years.",
    ),
    "sleep": (
        "Get a morning verdict on last night",
        "Nularo reads your sleep from Apple Health and delivers one honest, slightly rude verdict every morning. No logging, no pep talks.",
    ),
    "pet": (
        "A virtual pet that runs on your actual health data",
        "Nularo's creature lives on your Apple Health data. Sleep badly and it looks wrecked. Move and it glows. You never type anything in.",
    ),
    "habits": (
        "A habit tracker that does not need you to track",
        "Nularo reads your sleep and movement from Apple Health automatically, so the habit you are trying to build is the only thing you have to do.",
    ),
}


def store_url(ct):
    if PROVIDER_TOKEN:
        return f"https://apps.apple.com/app/apple-store/id{APP_ID}?pt={PROVIDER_TOKEN}&ct={ct}&mt=8"
    return f"https://apps.apple.com/us/app/nularo/id{APP_ID}"


def esc(s):
    return html.escape(s, quote=True)


def parse(path):
    text = path.read_text()
    m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->\s*(.*)", text, re.S)
    if not m:
        sys.exit(f"{path.name}: missing <!--meta {{...}} --> header")
    meta = json.loads(m.group(1))
    meta["slug"] = path.stem
    meta["body"] = m.group(2).strip()
    for key in ("title", "description", "cluster", "published"):
        if key not in meta:
            sys.exit(f"{path.name}: meta is missing '{key}'")
    if meta["cluster"] not in CLUSTERS:
        sys.exit(f"{path.name}: unknown cluster '{meta['cluster']}' (see guides/clusters.json)")
    meta.setdefault("updated", meta["published"])
    meta.setdefault("faq", [])
    meta.setdefault("related", [])
    return meta


def ct(surface, slug):
    return f"web_{surface}_{slug.replace('-', '_')}"[:40]


def cta_block(kind, slug, surface="gi"):
    head, body = CTA_COPY.get(kind, CTA_COPY["default"])
    return f"""<aside class="cta pane pane--ember">
  <img class="cta-creature" src="/img/creature-judgy.webp" alt="" width="96" height="96" loading="lazy" />
  <div>
    <p class="cta-head">{esc(head)}</p>
    <p>{esc(body)}</p>
    <a class="store-btn" href="{store_url(ct(surface, slug))}" data-cta="inline-{kind}">Get Nularo on the App Store</a>
    <p class="cta-fine">iPhone. Annual plan starts with a 3-day free trial.</p>
  </div>
</aside>"""


def shot_block(name):
    if name not in SHOTS:
        sys.exit(f"unknown screenshot '{name}', choose from {sorted(SHOTS)}")
    return f"""<figure class="screen">
  <img src="/img/app/{name}.webp" alt="{esc(SHOTS[name])}" width="600" height="1230" loading="lazy" />
  <figcaption>{esc(SHOTS[name])}.</figcaption>
</figure>"""


def expand(body, slug):
    body = re.sub(r"<!--\s*cta(?::(\w+))?\s*-->", lambda m: cta_block(m.group(1) or "default", slug), body)
    body = re.sub(r"<!--\s*shot:([\w-]+)\s*-->", lambda m: shot_block(m.group(1)), body)
    return body


def read_minutes(body):
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    return max(1, round(words / 230)), words


def nice_date(d):
    return dt.date.fromisoformat(d).strftime("%B %-d, %Y")


def head(title, description, canonical, extra=""):
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}" />
    <link rel="canonical" href="{canonical}" />
    <meta name="apple-itunes-app" content="app-id={APP_ID}" />
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="Nularo" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:image" content="{SITE}/img/hero-glowing.webp" />
    <meta name="twitter:card" content="summary" />
    <link rel="stylesheet" href="/style.css" />
{extra}  </head>"""


TOPBAR = """    <nav class="topbar">
      <div class="topbar-inner">
        <a class="wordmark" href="/">Nularo</a>
        <div class="navlinks">
          <a href="/guides/">Guides</a>
          <a class="nav-store" href="{store}" data-cta="nav">Get the app</a>
        </div>
      </div>
    </nav>"""

FOOTER = """    <footer class="sitefoot">
      <div class="sitefoot-inner">
        <a href="/guides/">Guides</a>
        <a href="/privacy.html">Privacy Policy</a>
        <a href="/terms.html">Terms of Service</a>
        <a href="/health-data-notice.html">Consumer Health Data Privacy Notice</a>
        <a href="/support.html">Support</a>
        <span class="spacer"></span>
        <span>Nularo by Sidewndr Studios</span>
      </div>
    </footer>"""

STICKY = """    <div class="sticky-cta" id="sticky-cta" hidden>
      <img src="/img/creature-glowing.webp" alt="" width="40" height="40" />
      <span>Nularo turns your Apple Health data into a creature that judges you.</span>
      <a class="store-btn store-btn--small" href="{store}" data-cta="sticky">Get it</a>
    </div>
    <script>
      (function () {{
        var bar = document.getElementById("sticky-cta");
        function onScroll() {{
          var h = document.documentElement;
          var p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
          bar.hidden = p < 0.18;
        }}
        window.addEventListener("scroll", onScroll, {{ passive: true }});
      }})();
    </script>"""

DISCLAIMER = (
    "Nularo is an entertainment and wellness app, not a medical device. Nothing on this "
    "page is medical advice. If something about your sleep or heart worries you, talk to a doctor."
)


def build_guide(g, all_guides):
    slug = g["slug"]
    url = f"{SITE}/guides/{slug}/"
    cluster = CLUSTERS[g["cluster"]]
    body = expand(g["body"], slug)
    minutes, words = read_minutes(body)
    g["words"] = words

    # related: explicit first, then newest in the same cluster, then newest anywhere
    by_slug = {x["slug"]: x for x in all_guides}
    rel = [by_slug[s] for s in g["related"] if s in by_slug and s != slug]
    for pool in (
        [x for x in all_guides if x["cluster"] == g["cluster"]],
        all_guides,
    ):
        for x in sorted(pool, key=lambda x: x["published"], reverse=True):
            if len(rel) >= 4:
                break
            if x["slug"] != slug and x not in rel:
                rel.append(x)
    related_html = "\n".join(
        f'<li><a href="/guides/{x["slug"]}/"><span>{esc(x["title"])}</span><small>{esc(CLUSTERS[x["cluster"]]["name"])}</small></a></li>'
        for x in rel
    )

    faq_html = ""
    if g["faq"]:
        items = "\n".join(
            f"<details><summary>{esc(q['q'])}</summary><p>{q['a']}</p></details>" for q in g["faq"]
        )
        faq_html = f'<h2 id="faq">Frequently asked questions</h2>\n<div class="faq">\n{items}\n</div>'

    hero_card = f'''<a class="hero-card" href="{store_url(ct('gh', slug))}" data-cta="hero">
          <img src="/img/creature-glowing.webp" alt="" width="44" height="44" />
          <span><strong>Nularo</strong> reads your Apple Health and turns it into a creature that reacts to how you really slept and moved.</span>
          <span class="hero-card-go">Get it</span>
        </a>'''

    tldr_html = ""
    if g.get("tldr"):
        tldr_html = f'<div class="tldr pane pane--violet"><p class="tldr-label">Short answer</p><p>{g["tldr"]}</p></div>'

    ld = [
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": g["title"],
            "description": g["description"],
            "datePublished": g["published"],
            "dateModified": g["updated"],
            "mainEntityOfPage": url,
            "image": f"{SITE}/img/hero-glowing.webp",
            "author": {"@type": "Organization", "name": "Nularo", "url": SITE},
            "publisher": {"@type": "Organization", "name": "Nularo", "url": SITE},
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Guides", "item": f"{SITE}/guides/"},
                {"@type": "ListItem", "position": 2, "name": cluster["name"], "item": f"{SITE}/guides/#{g['cluster']}"},
                {"@type": "ListItem", "position": 3, "name": g["title"], "item": url},
            ],
        },
    ]
    if g.get("howto"):
        ld.append(
            {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": g["title"],
                "step": [
                    {"@type": "HowToStep", "position": i + 1, "text": step}
                    for i, step in enumerate(g["howto"])
                ],
            }
        )
    if g["faq"]:
        ld.append(
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": q["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", q["a"])},
                    }
                    for q in g["faq"]
                ],
            }
        )
    ld_html = "".join(
        f'    <script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in ld
    )

    page = f"""{head(g.get('seo_title', g['title']), g['description'], url, ld_html)}
  <body>
{TOPBAR.format(store=store_url(ct('gn', slug)))}

    <main>
      <article class="wrap guide">
        <nav class="crumbs"><a href="/guides/">Guides</a> <span>/</span> <a href="/guides/#{g['cluster']}">{esc(cluster['name'])}</a></nav>
        <header class="doc-head">
          <h1>{esc(g['title'])}</h1>
          <p class="updated">Updated {nice_date(g['updated'])} · {minutes} min read</p>
        </header>
        {hero_card}
        {tldr_html}
{body}

        <h2>Try Nularo</h2>
{cta_block(g.get('cta', 'default'), slug, 'g').replace('data-cta="inline-', 'data-cta="end-')}
{faq_html}
        <p class="disclaimer">{DISCLAIMER}</p>

        <section class="related">
          <h2>Keep reading</h2>
          <ul>
{related_html}
          </ul>
        </section>
      </article>
    </main>

{FOOTER}
{STICKY.format(store=store_url(ct('gb', slug)))}
  </body>
</html>
"""
    dest = OUT / slug / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)


def build_index(guides):
    sections = []
    for key, c in CLUSTERS.items():
        items = [g for g in guides if g["cluster"] == key]
        if not items:
            continue
        lis = "\n".join(
            f'<li><a href="/guides/{g["slug"]}/"><span>{esc(g["title"])}</span><small>{esc(g["description"])}</small></a></li>'
            for g in sorted(items, key=lambda g: g["published"], reverse=True)
        )
        sections.append(
            f'<section id="{key}" class="cluster"><h2>{esc(c["name"])}</h2><p>{esc(c["blurb"])}</p><ul class="guide-list">\n{lis}\n</ul></section>'
        )
    store = store_url("web_guides_index")
    page = f"""{head('Guides: Apple Health, sleep data and habit apps explained · Nularo', 'Plain-English guides to the sleep, heart and movement data your iPhone and Apple Watch already collect, and to the apps that make it fun to look at.', f'{SITE}/guides/')}
  <body>
{TOPBAR.format(store=store)}

    <main>
      <div class="wrap">
        <header class="doc-head">
          <h1>Guides</h1>
          <p class="lede">Plain-English answers about the sleep, heart and movement data your iPhone and Apple Watch already collect, and the apps that make it worth looking at.</p>
        </header>
{chr(10).join(sections)}
{cta_block('default', 'index', 'guides')}
      </div>
    </main>

{FOOTER}
  </body>
</html>
"""
    (OUT / "index.html").write_text(page)


def build_meta_files(guides):
    today = dt.date.today().isoformat()
    urls = [
        (f"{SITE}/", today),
        (f"{SITE}/guides/", max([g["updated"] for g in guides], default=today)),
        (f"{SITE}/support.html", None),
        (f"{SITE}/privacy.html", None),
        (f"{SITE}/terms.html", None),
    ] + [(f"{SITE}/guides/{g['slug']}/", g["updated"]) for g in guides]
    rows = "\n".join(
        f"  <url><loc>{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>" for u, d in urls
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n'
    )
    bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot", "Amazonbot"]
    robots = "User-agent: *\nAllow: /\n\n" + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots)
    (ROOT / "robots.txt").write_text(robots + f"Sitemap: {SITE}/sitemap.xml\n")
    lines = [
        "# Nularo",
        "",
        "> Nularo is an iPhone app: a virtual creature that lives on your Apple Health data. It reads sleep, steps, "
        "workouts, resting heart rate and HRV automatically (no logging), reacts every morning with a blunt verdict "
        "on how you actually slept and moved, and computes a weekly Creature Age that rises when habits slip. "
        f"App Store: https://apps.apple.com/us/app/nularo/id{APP_ID}",
        "",
        "## Guides",
        "",
    ] + [
        f"- [{g['title']}]({SITE}/guides/{g['slug']}/): {g['description']}"
        for g in sorted(guides, key=lambda g: g["published"], reverse=True)
    ]
    (ROOT / "llms.txt").write_text("\n".join(lines) + "\n")


def check(guides):
    problems = []
    slugs = {g["slug"] for g in guides}
    for f in [ROOT / "index.html", OUT / "index.html"] + [OUT / g["slug"] / "index.html" for g in guides]:
        text = f.read_text()
        if "—" in text:
            problems.append(f"{f.relative_to(ROOT)}: contains an em dash")
        for href in re.findall(r'href="(/guides/[^"#]*)', text):
            s = href.strip("/").split("/")
            if len(s) == 2 and s[1] not in slugs:
                problems.append(f"{f.relative_to(ROOT)}: broken internal link {href}")
    for g in guides:
        if len(g["title"]) > 70:
            problems.append(f"{g['slug']}: title over 70 chars")
        if not 70 <= len(g["description"]) <= 165:
            problems.append(f"{g['slug']}: description should be 70-165 chars (is {len(g['description'])})")
        if g.get("words", 0) < 700:
            problems.append(f"{g['slug']}: only {g.get('words')} words")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("check passed")


def main():
    guides = sorted((parse(p) for p in SRC.glob("*.html")), key=lambda g: g["published"])
    for g in guides:
        build_guide(g, guides)
    build_index(guides)
    build_meta_files(guides)
    print(f"built {len(guides)} guides")
    if "--check" in sys.argv:
        check(guides)


if __name__ == "__main__":
    main()
