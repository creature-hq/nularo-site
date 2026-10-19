# The Nularo guide engine

One guide a day, written and published by Claude, aimed at a query a brand-new
site can actually win. Copied from Rasty Turek's Vaultaire loop (Starter Story,
Oct 2026; site teardown of vaultaire.app on 2026-10-19), adapted for Nularo.

This file is the instruction set for the daily run. Read all of it every run.

## The daily run, in order

1. `git pull`. Read this file, `seo/backlog.json`, `seo/log.md`, and the list of
   existing guides in `guides/src/`.
2. **Pick today's target.**
   - Run `python3 tools/gsc_opportunities.py`. If it prints opportunities, they
     win: a query with impressions and position deeper than 15 that no guide
     targets becomes today's new guide. A query on page 1 with CTR under 2% means
     the existing page's `seo_title` and `description` get rewritten instead (do
     that as well, it is cheap).
   - With no credentials or no opportunities, take the lowest `priority` number
     in `seo/backlog.json` whose `status` is `todo`.
   - Never write two guides for the same intent. If a guide already covers it,
     deepen that guide instead (add a section, update `updated`).
3. **Research before writing.** Search the query. Read the top results. Note what
   they all miss, what is outdated (old iOS menus), and what Reddit/Apple
   Community askers actually wanted. Check every iPhone/Apple Watch menu path
   against support.apple.com. If a fact cannot be verified, leave it out.
4. **Write the guide** to `guides/src/<slug>.html` using the skeleton below.
5. **Link it in.** Edit 2-4 existing guides (highest traffic first once Search
   Console data exists, otherwise the same cluster's pillar) to add a natural
   inline link with a descriptive anchor. Bump their `updated` date only if you
   changed real content.
6. `python3 tools/build.py --check`. Fix anything it reports.
7. Mark the backlog item `done` with the date, append one line to `seo/log.md`
   (date, slug, target query, why it was chosen, which pages now link to it).
8. Commit (`Add guide: <title>`) and push to `main`. GitHub Pages deploys in about
   a minute.

One guide per day. Not five. Rasty's point was that Google rewards a steady
trickle of good pages over a flood.

## The guide skeleton (Vaultaire's Era 2 template)

Source file: a JSON meta header, then the body HTML.

```html
<!--meta
{
  "title": "H1, the plain question or how-to, 40-65 chars",
  "seo_title": "Title tag if it should differ (add the year or a hook), max 60",
  "description": "70-160 chars. States the answer, does not tease it.",
  "keyword": "the exact target query",
  "cluster": "one key from guides/clusters.json",
  "published": "YYYY-MM-DD",
  "updated": "YYYY-MM-DD",
  "tldr": "The ~60-90 word direct answer with exact menu paths. Must stand alone: this is what Google's snippet and AI Overviews lift.",
  "howto": ["Step 1 text", "Step 2 text"],
  "cta": "default | age | sleep | pet | habits",
  "faq": [{"q": "...", "a": "2-3 sentences"}],
  "related": ["slug-a", "slug-b"]
}
-->
<p class="lede">A second-person scenario hook. "You wake up, check your Apple Watch, and..."</p>
<h2>...</h2>
...
```

Body order:
1. `<p class="lede">` hook: the reader's situation in one or two sentences.
2. 3-5 `<h2>` sections, sentence case, 150-300 words each. **The free or built-in
   answer comes first** (what the iPhone, Apple Watch or Health app already does,
   with exact menu paths). This is what earns the ranking.
3. One section, late, where Nularo comes in honestly: what it does for this exact
   problem, a real screenshot (`<!-- shot:NAME -->`), and **one honest limitation**
   (iPhone only; needs Apple Health data, so no watch means thinner data; morning-after,
   not real time; it judges, it does not coach). Then `<!-- cta:KIND -->`.
4. `<h2>Sources</h2>` with 2-3 links to primary sources (support.apple.com first,
   then official docs or peer-reviewed sources). External links get `rel="noopener"`.
5. FAQ lives in the meta (`faq`), 3-5 questions; the last one may be about Nularo.

Length: 1,000-1,600 words. `build.py --check` fails under 700.

Internal links: 4-8 per guide to other guides, inline, with descriptive anchors
(the target page's topic, never "click here"). Link only to guides that exist.

## Screenshots available

`<!-- shot:NAME -->` for: `age-tab`, `overview`, `creature`, `today`,
`milestones`, `onboarding-creature-age`, `connect-apple-health`. Use at most two
per guide, and only where the screen actually shows what the paragraph says.

## Hard rules (Nularo's, they override everything)

- **No medical advice, ever.** Explain what a metric is and where to find it.
  Never tell the reader what to do about their health, never diagnose, never
  suggest treatments, supplements, dosages or "fixes" for conditions (insomnia,
  apnea, ADHD, depression). Wellness explainers cite Apple or a public-health body
  and stop there. Anything worrying gets "talk to a doctor".
- **Only verified product claims about Nularo.** True today: iPhone only; reads
  Apple Health read-only (sleep, sleep stages, steps, active minutes, workouts,
  resting heart rate, HRV, respiratory rate, SpO2); no manual logging required;
  morning verdict notification; four moods (glowing, fine-but-judgy, wrecked,
  suspicious) set against your own 14-day baseline; Creature Age recalculated
  weekly from sleep duration (anchored at 7h30 a night), bedtime consistency,
  steps (8,000 a day), active minutes (30 a day), resting heart rate and HRV,
  with a per-habit breakdown of the years added; a good stretch can make the
  creature up to 1.5 years younger than you; hidden until 7 days of data exist;
  the app is a subscription (hard paywall after onboarding); Sleep, Stress and Energy
  scores; sleep debt; Bedtime Pledge; evening Confessions; Weekly Report Card;
  shareable roast cards; friend mode (a friend sees only a mood word and a
  good-day count, never health numbers); optional journal; $39.99/year with a
  3-day free trial, or $9.99/month. Anything else: do not claim it.
- Never claim Nularo is medical, clinical, a coach, or "scientifically proven".
  Creature Age is a rules-based, for-fun number built from public-health
  guidelines; say so when it matters.
- Competitors get described fairly and accurately (check their current App Store
  page before stating price or features). No invented ratings.
- **No em dashes anywhere.** Use commas, periods, parentheses. `--check` fails on them.
- No AI tells: no "in today's fast-paced world", "delve", "it's important to note",
  "game-changer", "unlock", "dive in", "navigate the complexities". Short sentences.
  Specific numbers. The voice is a smart friend who has read the Apple docs, with
  a little of the creature's dryness.
- Never invent statistics, studies, quotes or user stories.
