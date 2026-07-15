# lauris.xyz

Personal site for Lauris. Static HTML, no framework, no deploy-time build step.

## Structure

- `index.html` — the front page (self-contained: inline CSS/JS, including the section-03 state-space canvas scene).
- `writing/` — the writing archive: `writing/index.html` plus one directory per article (`writing/<slug>/index.html`). **Generated — don't hand-edit.**
- `assets/` — project screenshots; `assets/writing/` — article heroes and inline figures.
- `tools/build_writing.py` — generates everything under `writing/` from `tools/data/articles.json` (full article text pulled from X) plus the per-article config (slugs, decks, figure placement, related links) at the top of the script.

## Edit

- Front page: edit `index.html` directly.
- Articles/archive: edit `tools/build_writing.py` (config or template) or `tools/data/articles.json`, then run `python3 tools/build_writing.py` and commit the regenerated output.

## Deploy

- Hosted on Vercel project **`quickpg`** (Insrt team), serving the custom domains `lauris.xyz` + `www.lauris.xyz`.
- Git-connected to this repo, production branch `main`. Push to `main` → auto-deploys to production.
- Vercel serves the committed HTML directly; the generator never runs at deploy time.
