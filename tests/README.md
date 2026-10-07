# Tests

Browser tests (Playwright + Chrome). Screenshots go to `tests/output/` (git-ignored). `/tests/*` is redirected
home on the live site (`_redirects`), so these are only in the repo.

**Local** (start the preview server first: `.claude/launch.json` → `xz-dance-practice`, i.e. `python -m http.server 8889`):

| Script | Checks |
|---|---|
| `smoke_local.py` | single-MV page, `?s=N` links, 2-MV catalog (second MV faked by routing), bad slug, mark mode, phone layout. The only expected 404s are `favicon.ico` and the deliberate `mvs/nope.json`. |
| `parts_tabs.py` | part tabs on one row at 320 / 375 / 1280 px, restart a part, 所有段落, A–B interplay |
| `controls_row.py` | Play + speeds on one row (speeds sit ~5 px lower in their segmented track), nothing clipped, fullscreen bar |
| `play_label.py` | Play / Cancel / Pause labels (incl. the first count-in), header + tab title |
| `source_links.py` | Weibo / Douyin links side by side on phones, no sideways scroll |
| `nudge_fullscreen.py` | 10-minute nudge (timer sped up), fullscreen, opening the official MV from the nudge |

**Live** (`https://xz-dance-room.pages.dev`):

| Script | Checks |
|---|---|
| `live_smoke.py` | video from the CDN, part tap, Douyin embed, shared `?s=3` link, robots.txt |
| `live_redirects_ga.py` | `/CLAUDE.md`, `/tools/*`, `/.gitignore` redirect home; Google Analytics page_view for G-T79K5T7M9N |
| `engines_speed.py` | measured playback speed at 0.5× / 0.75× in Chromium, Firefox, WebKit (Firefox/WebKit need `python -m playwright install firefox webkit`) |

Run any of them with `python tests/<name>.py`. They print results; read them, they don't assert.
