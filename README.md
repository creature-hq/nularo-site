# nularo-site

The public legal + landing pages for [Nularo](https://nularo.com), served via GitHub Pages.

Kept as its own repo (separate from `creature-app`) because it's static, has no
secrets, and reviewers/lawyers/users hitting `nularo.com` should never touch the
app's build pipeline.

- `index.html` — landing page
- `privacy.html` — Privacy Policy
- `terms.html` — Terms of Service

`src/constants/legal.ts` in `creature-app` points at these exact URLs
(`https://nularo.com/privacy.html`, `https://nularo.com/terms.html`) and they're
also wired into the Superwall dashboard paywall's Terms/Privacy buttons — if a
filename here ever changes, update both of those too.

To edit: change the HTML here, commit, push to `main`. GitHub Pages redeploys
automatically in about a minute.
