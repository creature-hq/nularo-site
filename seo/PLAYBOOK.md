# The Nularo guide engine

Two guides a day, written and published by Claude, each aimed at a query a
brand-new site can actually win. The cloud routine runs twice a day and each
run writes ONE guide: the **morning slot** (run starts before 16:00 UTC) and the
**evening slot** (run starts 16:00 UTC or later). See "Which slot am I" below. Copied from Rasty Turek's Vaultaire loop (Starter Story,
Oct 2026; site teardown of vaultaire.app on 2026-10-19), adapted for Nularo.

This file is the instruction set for every run. Read all of it every run.

## Which slot am I

Check `date -u +%H`. The two slots pick targets differently so the site grows
from both data and real people:

- **Morning slot (data):** step 2 rules a, then b, then c. If it is Monday,
  do the weekly review (step 0) first.
- **Evening slot (people):** step 2 rule t (trending) first, then rule r
  (Reddit questions), and only if neither finds a winnable target, fall back to
  a, b, c. If the morning run already published today (check `seo/log.md`),
  never pick the same intent or the same cluster's very next backlog item twice.

## The run, in order

0. **Weekly review (Monday morning slot only). This is the feedback loop that
   makes the engine improve over time.** Before picking today's target:
   - From `seo/gsc-latest.json` `pages`: any guide with 20+ impressions and
     0 clicks gets a sharper `seo_title` and `description` (match the queries
     it actually shows for in `queries`). Any guide at position 8 to 20 gets one
     deeper section that answers what the top results answer and it does not.
   - If `seo/link-report.md` (weekly broken-link check) lists broken external
     links, fix or remove them.
   - Update `seo/learnings.md`: for each cluster and each pick rule (a, b, c,
     t, r), how many guides, total impressions and clicks, and which guides
     earned anything. Write 3 short lines at the top: what is working, what is
     not, and what the next week will do more of (for example "Reddit-picked
     guides get 3x the impressions of backlog guides, so the evening slot keeps
     rule r first"). Later runs read the top of this file in step 1 and lean
     their picks toward what is working.
   - Commit these edits together with the day's guide.
1. `git pull`. Read this file, `seo/backlog.json`, `seo/log.md`, the top of
   `seo/learnings.md`, and the list of existing guides in `guides/src/`.
2. **Pick today's target. This is Rasty's loop: "your site was showed 16,000
   times for this keyword, but no clicks because you are like number 50", so
   write the guide for that keyword.** A GitHub Action pulls Google data every
   morning before this run (this sandbox cannot reach Google, so do not run
   the tools yourself) into two files:
   - `seo/gsc-latest.json` (Search Console, last 28 days): `totals`,
     `opportunities` (5+ impressions and position deeper than 8 or CTR under 2%),
     `pages` (busiest first), `queries` (everything Google showed us for) and
     `index` (Google's verdict on each guide).
   - `seo/keywords-latest.json` (Google Autocomplete, the free stand-in for
     Rasty's Keyword Planner): `backlog_demand` (whether each todo keyword is
     a phrase people actually type: Google only echoes it back if they do, and
     a higher `suggestion_count` means more demand around it) and
     `new_candidates` (long-tail phrases people type around our clusters that
     are not in the backlog yet, most-seen first).

   Pick in this order, and say in the log which rule picked it:
   a. **Search Console opportunity** (if `pulled` is within 3 days). A query
      with `action: "new guide"` (position deeper than 15) that no guide
      targets becomes today's guide. For a page-1 query with CTR under 2%,
      rewrite that page's `seo_title` and `description` to match the query
      as well (cheap, do it on top of the new guide). Also scan `queries`: a
      query that keeps showing up for a page that does not really answer it
      is an opportunity even below 5 impressions.
   b. **Backlog, demand-checked.** Otherwise take the lowest `priority`
      number with `status: "todo"` whose entry in `backlog_demand` has
      `exact_in_autocomplete: true`. Skip ones that are false (nobody types
      that phrase; consider retargeting the item to the closest phrase in its
      `suggestions` instead). If the keyword is not in `backlog_demand`
      (it is checked 40 at a time), use it but say so in the log.
   c. **Top up the backlog.** When fewer than 30 todo items are left, add
      up to 10 of the best `new_candidates` to `seo/backlog.json` (same
      fields as existing items; check the current results are weak, like
      forums, Reddit and App Store listings, before adding). Hyper-niche beats
      broad: a phrase that names a device, a demographic or a specific
      situation ("for night shift workers", "for couples", "on Apple Watch")
      is one a brand-new site can win.
   t. **Trending (evening slot first).** Search news and social from the last
      7 days for our clusters: Apple Health, Apple Watch and watchOS/iOS
      updates, sleep and habit trends (the way "sleepmaxxing" took off), virtual
      pet and companion apps, and competitors (Finch, Pengu, Bevel, Whoop,
      Oura). Use WebSearch with words like "this week", the month and year, and
      `site:reddit.com` for the last week. A topic wins if people are clearly
      asking about it right now, it fits a cluster, and the current results are
      thin or outdated (old iOS menus, news posts with no how-to). New releases
      win fastest: the first good how-to after an Apple update often ranks
      before big sites write one. Only claims you can verify, as always.
   r. **Reddit questions (evening slot second).** Reddit is where people talk
      about these topics all day. Start with `seo/reddit-latest.json`, pulled
      daily at 15:00 UTC by a GitHub Action from 10 subreddits (r/AppleWatch,
      r/sleep, r/ouraring, r/whoop, r/finch, r/nightshift, r/getdisciplined and
      more): `themes` are word pairs shared by 3+ separate question titles
      (the "asked over and over" signal, with example titles), `questions` are
      the topic-matching questions of the last 7 days, most discussed first,
      with links and an excerpt. Read the threads behind a promising theme
      (full network access is on) before deciding. Skip themes that are
      medical (waking at 3am, insomnia) unless the guide can stay a pure
      "what the metric is and where to find it" explainer. As a backup, search
      `site:reddit.com` for each cluster's
      seed terms (r/AppleWatch, r/sleep, r/applehealth, r/getdisciplined,
      r/selfimprovement, r/ios and similar) and look for the question asked
      over and over in separate threads (3+ threads asking the same thing in
      different words is the signal). Write the guide that answers it fully.
      Add the exact phrasing people use as the `keyword`, and add the other
      repeat questions you find to `seo/backlog.json` with `"source": "reddit"`
      so later runs can use them. Never quote or name Reddit users.
   - Free tools beat articles when the query is a calculation ("calculator",
     "how to calculate", "how much sleep debt do I have"). If you find one, you
     may build a small tool page instead of a plain guide: the same guide
     skeleton plus a plain HTML/JS calculator in the body (no external
     scripts, no data sent anywhere), with the math shown below it and sourced.
   - Never write two guides for the same intent. If a guide already covers it,
     deepen that guide instead (add a section, update `updated`).
3. **Research before writing.** Search the query. Read the top results. Note what
   they all miss, what is outdated (old iOS menus), and what Reddit/Apple
   Community askers actually wanted. Check every iPhone/Apple Watch menu path
   against support.apple.com. If a fact cannot be verified, leave it out.
4. **Write the guide** to `guides/src/<slug>.html` using the skeleton below.
5. **Link it in.** This is how Rasty gets new guides prioritized: "the internal
   links from existing traffic point to the new guides." Edit 2-4 existing
   guides to add a natural inline link with a descriptive anchor. Choose them
   in this order: the busiest pages in `gsc-latest.json` `pages`; then guides
   whose `index` verdict is `PASS` (Google already trusts them, so their links
   get followed); then the same cluster's pillar. While any guide in `index`
   is "Crawled - currently not indexed" or "URL is unknown to Google", also
   make sure at least two indexed guides link to it (add one such link per
   run, in a guide you are already editing). Bump `updated` dates only if you
   changed real content.
6. `python3 tools/build.py --check`. Fix anything it reports. The build also links every
   new guide from the homepage and from the "New guides" footer on every guide
   page, and pushes to main ping IndexNow, so step 5's inline links are the
   only linking you do by hand. The slug `how-we-write` is reserved.
7. Mark the backlog item `done` with the date, append one line to `seo/log.md`
   (date, slot (morning/evening), slug, target query, which rule picked it
   (a/b/c/t/r) and why, which pages
   now link to it, and today's `totals` plus how many guides are indexed, so the
   log doubles as the traffic history).
8. Commit (`Add guide: <title>`) and push to `main`. GitHub Pages deploys in about
   a minute.

Two guides per day (one per slot). Not five. Rasty's point was that Google
rewards a steady trickle of good pages over a flood, so quality stays the bar:
every guide has to be better than what ranks today.

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
