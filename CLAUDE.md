# CLAUDE.md — RayDar Vice

Sibling of the canonical RayDar repo (AI_valuechain); its working rules apply here too.

## Hosting (split repos, 2026-10-25)

- This code lives in a PRIVATE source repo (RayDar-Vice-src). The PUBLIC repo
  miikawir-ops/RayDar-Vice holds only the published pages and is served by
  GitHub Pages from main/root, so old links (e.g. /RayDar-Vice/raydar_vice.html)
  keep working.
- The workflow builds the curated set in `_site/` (index.html, raydar_vice.html,
  quantum.html — paths preserved) and `tools/publish_site.py` pushes it to the
  public repo with the `SITE_DEPLOY_KEY` deploy key (write access to that repo
  only). It skips while the secret is missing and fails the run if the push fails.
- Never push this repo, or any folder containing code or data, to the public
  site repo. The publisher refuses .py/.md/.json/.jsonl/workflow files and keeps
  CNAME and .nojekyll. A new page is published only by adding it to the
  "Prepare curated site" step.
- `seen_hashes.json`, `signal_history.json`, `templates/` and `scripts/` stay
  private. The published set must contain index.html (it redirects to
  raydar_vice.html) so the bare URL resolves.
- `tools/publish_site.py` is a byte-identical copy of AI_valuechain's; its test
  lives there (test_publish_site.py). Update both together.
