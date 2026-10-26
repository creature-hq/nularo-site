#!/usr/bin/env python3
"""Build the Nularo guides.

Stdlib only, on purpose: the daily agent runs this in a fresh cloud
checkout with nothing installed.

Source:  guides/src/<slug>.html  = a JSON header in an HTML comment,
         then the article body as plain HTML.
Output:  guides/<slug>/index.html, guides/index.html, guides/how-we-write/,
         404.html, sitemap.xml, robots.txt, llms.txt, and the guide list
         between <!-- guides:start/end --> on the homepage.

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


def head(title, description, canonical, extra="", og_type="article"):
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}" />
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1" />
    <link rel="canonical" href="{canonical}" />
    <meta name="apple-itunes-app" content="app-id={APP_ID}" />
    <meta property="og:type" content="{og_type}" />
    <meta property="og:site_name" content="Nularo" />
    <meta property="og:title" content="{esc(title)}" />
    <meta property="og:description" content="{esc(description)}" />
    <meta property="og:url" content="{canonical}" />
    <meta property="og:image" content="{SITE}/img/hero-glowing.webp" />
    <meta property="og:image:alt" content="Nularo's creature, glowing" />
    <meta name="twitter:card" content="summary_large_image" />
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
{newest}
      <div class="sitefoot-inner">
        <a href="/guides/">Guides</a>
        <a href="/guides/how-we-write/">How we write guides</a>
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

# how many of the newest guides every guide page lists in its footer. New
# guides start with no links from Google's point of view; this gives each
# one a link from every page on the site on the day it ships.
FOOTER_NEWEST = 6
# the homepage lists this many newest guides, then links to the rest
HOME_GUIDES = 30


def footer(guides):
    newest = sorted(guides, key=lambda g: g["published"], reverse=True)[:FOOTER_NEWEST]
    lis = "\n".join(f'          <li><a href="/guides/{g["slug"]}/">{esc(g["title"])}</a></li>' for g in newest)
    block = f"""      <nav class="sitefoot-guides" aria-label="New guides">
        <p>New guides</p>
        <ul>
{lis}
        </ul>
      </nav>""" if newest else ""
    return FOOTER.format(newest=block)


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
            "inLanguage": "en",
            "wordCount": words,
            "isPartOf": {"@type": "WebSite", "@id": f"{SITE}/#website", "name": "Nularo", "url": f"{SITE}/"},
            "about": {"@type": "MobileApplication", "@id": f"{SITE}/#app", "name": "Nularo"},
            "image": f"{SITE}/img/hero-glowing.webp",
            "author": {"@type": "Organization", "@id": f"{SITE}/#org", "name": "Nularo", "url": f"{SITE}/"},
            "publisher": {"@type": "Organization", "@id": f"{SITE}/#org", "name": "Nularo", "url": f"{SITE}/", "logo": {"@type": "ImageObject", "url": f"{SITE}/img/creature-glowing.webp"}},
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
          <p class="updated">Updated {nice_date(g['updated'])} · {minutes} min read · <a href="/guides/how-we-write/">How we write these</a></p>
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

{footer(all_guides)}
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
    ordered = sorted(guides, key=lambda g: g["published"], reverse=True)
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Nularo guides",
        "url": f"{SITE}/guides/",
        "isPartOf": {"@type": "WebSite", "@id": f"{SITE}/#website", "name": "Nularo", "url": f"{SITE}/"},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(ordered),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": f"{SITE}/guides/{g['slug']}/", "name": g["title"]}
                for i, g in enumerate(ordered)
            ],
        },
    }
    ld_html = f'    <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
    page = f"""{head('Apple Health, Sleep and Habit App Guides (2026) · Nularo', 'Plain-English guides to the sleep, heart and movement data your iPhone and Apple Watch already collect, and to the apps that make it fun to look at.', f'{SITE}/guides/', ld_html, 'website')}
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

{footer(guides)}
  </body>
</html>
"""
    (OUT / "index.html").write_text(page)


def build_home(guides):
    """Fill the guide list between the markers on the hand-written homepage.
    The homepage is the page Google trusts most, so every guide it links to
    gets found and crawled sooner."""
    home = ROOT / "index.html"
    text = home.read_text()
    start, end = "<!-- guides:start -->", "<!-- guides:end -->"
    if start not in text or end not in text:
        sys.exit("index.html is missing the <!-- guides:start/end --> markers")
    ordered = sorted(guides, key=lambda g: g["published"], reverse=True)
    lis = "\n".join(
        f'            <li><a href="/guides/{g["slug"]}/"><span>{esc(g["title"])}</span><small>{esc(CLUSTERS[g["cluster"]]["name"])}</small></a></li>'
        for g in ordered[:HOME_GUIDES]
    )
    more = f'\n          <p class="home-more"><a href="/guides/">All {len(ordered)} guides &rarr;</a></p>' if len(ordered) > HOME_GUIDES else ""
    block = f"""{start}
          <ul class="guide-list">
{lis}
          </ul>{more}
          {end}"""
    text = text[: text.index(start)] + block + text[text.index(end) + len(end):]
    home.write_text(text)


def build_404(guides):
    ordered = sorted(guides, key=lambda g: g["published"], reverse=True)[:8]
    lis = "\n".join(
        f'<li><a href="/guides/{g["slug"]}/"><span>{esc(g["title"])}</span><small>{esc(g["description"])}</small></a></li>'
        for g in ordered
    )
    page = f"""{head('Page not found · Nularo', 'This page does not exist. Try the Nularo guides to Apple Health, sleep data and habit apps.', f'{SITE}/404.html', '', 'website').replace('index, follow, max-image-preview:large, max-snippet:-1', 'noindex, follow')}
  <body>
{TOPBAR.format(store=store_url('web_404'))}

    <main>
      <div class="wrap">
        <header class="doc-head">
          <h1>The creature looked everywhere. Nothing here.</h1>
          <p class="lede">That page does not exist, or it moved. These might be what you were after.</p>
        </header>
        <ul class="guide-list">
{lis}
        </ul>
        <p><a href="/guides/">All guides &rarr;</a></p>
      </div>
    </main>

{footer(guides)}
  </body>
</html>
"""
    (ROOT / "404.html").write_text(page)


HOW_WE_WRITE = f"""<p class="lede">Every guide on this site answers one question people actually search for, about the health data an iPhone and Apple Watch already collect or the apps that use it.</p>
<h2>Where the facts come from</h2>
<p>Settings paths, metric definitions and feature availability are checked against Apple's own support pages and developer documentation. Competitor prices and features are checked against each app's current App Store listing on the day the guide is written. If a fact cannot be checked, it is left out.</p>
<h2>How we treat other apps</h2>
<p>Nularo makes an app, and these guides compare it with apps it competes with. We say what each one does well, including where another app is the better pick for you. We do not invent ratings, reviews, user stories or statistics.</p>
<h2>No medical advice</h2>
<p>These guides explain what a number is and where to find it. They do not diagnose anything, suggest treatments or tell you what to do about your health. Wellness explainers cite Apple or a public-health body. If something about your sleep or heart worries you, talk to a doctor.</p>
<h2>Keeping guides current</h2>
<p>Apps and watchOS change. When a guide is revised with real changes, its updated date changes too. Spot something wrong or out of date? Email <a href="mailto:sidewndrstudios@gmail.com">sidewndrstudios@gmail.com</a> and we will fix it.</p>"""


def build_how_we_write(guides):
    url = f"{SITE}/guides/how-we-write/"
    page = f"""{head('How We Write Nularo Guides', 'How Nularo researches, checks and updates its guides to Apple Health data and health apps, and how we treat competing apps.', url, '', 'website')}
  <body>
{TOPBAR.format(store=store_url('web_how_we_write'))}

    <main>
      <article class="wrap guide">
        <nav class="crumbs"><a href="/guides/">Guides</a></nav>
        <header class="doc-head">
          <h1>How we write these guides</h1>
        </header>
{HOW_WE_WRITE}
      </article>
    </main>

{footer(guides)}
  </body>
</html>
"""
    dest = OUT / "how-we-write" / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(page)


def build_meta_files(guides):
    today = dt.date.today().isoformat()
    urls = [
        (f"{SITE}/", today),
        (f"{SITE}/guides/", max([g["updated"] for g in guides], default=today)),
        (f"{SITE}/guides/how-we-write/", None),
        (f"{SITE}/support.html", None),
        (f"{SITE}/privacy.html", None),
        (f"{SITE}/terms.html", None),
        (f"{SITE}/health-data-notice.html", None),
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
    slugs = {g["slug"] for g in guides} | {"how-we-write"}
    pages = [ROOT / "index.html", ROOT / "404.html", OUT / "index.html", OUT / "how-we-write" / "index.html"]
    for f in pages + [OUT / g["slug"] / "index.html" for g in guides]:
        text = f.read_text()
        if "—" in text:
            problems.append(f"{f.relative_to(ROOT)}: contains an em dash")
        for href in re.findall(r'href="(/guides/[^"#]*)', text):
            s = href.strip("/").split("/")
            if len(s) == 2 and s[1] not in slugs:
                problems.append(f"{f.relative_to(ROOT)}: broken internal link {href}")
    home = (ROOT / "index.html").read_text()
    for g in sorted(guides, key=lambda g: g["published"], reverse=True)[:HOME_GUIDES]:
        if f'href="/guides/{g["slug"]}/"' not in home:
            problems.append(f"index.html: homepage does not link {g['slug']}")
    for g in guides:
        if g["slug"] == "how-we-write":
            problems.append("how-we-write is reserved for the editorial page, pick another slug")
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
    guides = sorted((parse(p) for p in sorted(SRC.glob("*.html"))), key=lambda g: g["published"])
    for g in guides:
        build_guide(g, guides)
    build_index(guides)
    build_home(guides)
    build_404(guides)
    build_how_we_write(guides)
    build_meta_files(guides)
    print(f"built {len(guides)} guides")
    if "--check" in sys.argv:
        check(guides)


if __name__ == "__main__":
    main()
