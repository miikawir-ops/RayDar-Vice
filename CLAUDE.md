# CLAUDE.md — RayDar Vice

Sibling of the canonical RayDar repo (AI_valuechain); its working rules apply here too.

## Hosting

- The repo is public and stays public (Ray, 2026-10-25). No license: all rights
  reserved (see README.md).
- GitHub Pages serves a curated artifact, not the repo: the workflow copies
  index.html (redirects to raydar_vice.html), raydar_vice.html (regenerated
  daily) and quantum.html into `_site/` and deploys it (Pages source: "GitHub
  Actions"). Paths are preserved, so old links keep working; code, templates and
  the JSON state files (seen_hashes.json, signal_history.json) are not served.
- Custom domain (2026-10-27): https://vice.raydar.fi/, HTTPS enforced. Old
  miikawir-ops.github.io/RayDar-Vice/ URLs 301-redirect with paths preserved.
  Siblings: https://raydar.fi/ and https://datacenter.raydar.fi/; link them by
  these domains. The TP_special_agent link stays on github.io.
- Before a domain or hosting cutover, probe only throwaway paths over http (e.g. /probe-123.html), never / or real pages: GitHub's CDN caches the pre-cutover 404 for an unknown time.
- A new page is published only by adding it to the "Prepare Pages artifact" step.
  After any deploy, check the root and the page you changed.
- index.html must stay in the published set so the bare URL resolves; the daily
  workflow must not overwrite it.
- Keep secrets out of git (.env is ignored; GEMINI_API_KEY is a repo secret).
- Bot commits use github-actions[bot] (41898282+github-actions[bot]@users.noreply.github.com).
