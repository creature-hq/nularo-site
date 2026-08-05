# nularo-site

The public legal + landing pages for [Nularo](https://nularo.com), served via GitHub Pages.

Kept as its own repo (separate from `creature-app`) because it's static, has no
secrets, and reviewers/lawyers/users hitting `nularo.com` should never touch the
app's build pipeline.

- `index.html` — landing page
- `privacy.html` — Privacy Policy
- `terms.html` — Terms of Service
- `health-data-notice.html` — Consumer Health Data Privacy Notice (Washington's My
  Health My Data Act requires this be a separate document from the Privacy Policy)
- `style.css` — the frosted-ember system, adapted for the web. Every colour is
  copied verbatim from `creature-app/src/constants/theme.ts`; if the app's palette
  ever moves, this drifts out of sync and should be re-copied by hand (there's no
  build step tying the two together).
- `img/` — the creature renders used on the landing page, exported from
  `creature-app/assets/character/*.png` as resized, compressed WebP.

`src/constants/legal.ts` in `creature-app` points at these exact URLs
(`https://nularo.com/privacy.html`, `https://nularo.com/terms.html`,
`https://nularo.com/health-data-notice.html`) and the first two are also wired
into the Superwall dashboard paywall's Terms/Privacy buttons — if a filename here
ever changes, update both of those too.

To edit: change the HTML/CSS here, commit, push to `main`. GitHub Pages redeploys
automatically in about a minute.
