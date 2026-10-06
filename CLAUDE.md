# XZ 舞蹈练习室 · Dance with Xiao Zhan (XZ Dance Room)

A static page that helps the fan group learn Xiao Zhan's MV dances: slow the video down with the pitch kept, loop a dance part, mirror it, and hear a "5、6、7、8" count-in on the song's beat. The UI is in Chinese with small English underneath.

- **Local folder:** `XZ Dance Practice/` (the name is kept on purpose).
- **Repo / site:** public repo `canadaxfx/xz-dance-room` → Cloudflare Pages `xz-dance-room.pages.dev` (live since 2026-10-06). Every push to `main` deploys automatically; there is no GitHub Pages mirror. Push with autosync's GitHub token (`C:\AI Tools\xz-autosync\config.json`, fine-grained, all repos, Contents read/write) passed as a one-off `http.extraheader` — never store it in the remote URL. That token cannot create repos (create new repos on github.com).
- **Search engines:** findable, like the other XZ sites: `noai, noimageai` meta plus the shared AI-crawler `robots.txt`.
- **Local preview:** `.claude/launch.json` → `xz-dance-practice`, which runs `python -m http.server 8889`.

## Files

| Path | What |
|------|------|
| `index.html` | The whole app: CSS + JS inline, no build step. |
| `mvs/index.json` | The catalog: `{"mvs":[{slug,title,titleEn,released,poster,sections,danceSeconds}]}`. `make_cut.py` updates it. |
| `mvs/<slug>.json` | One file per MV (schema below). |
| `fonts/big-shoulders-display-800.woff2` | Self-hosted (Latin subset), because Google Fonts is unreachable in China. |
| `tools/make_cut.py` | Builds the practice cut, verifies it, uploads it, and updates both JSON files. |
| `tools/bpm.py` | Measures the song's tempo for the count-in. |
| `_backup/` | Old versions. Git-ignored, and so is `*.bak*`. |

## Routing

- **No `?mv=`, 2+ MVs:** shows the home catalog of MV cards.
- **No `?mv=`, only one MV:** opens that MV directly. There is no catalog and no back link.
- **`?mv=<slug>`:** opens that MV's practice room. "← 全部 MV" appears only when there are 2+ MVs.
  - The slug must match `^[a-z0-9-]{1,40}$`.
  - An unknown slug shows the catalog with a "not found" line.
- **`&s=N`:** selects part N and waits at its start, with loop on and no autoplay. Tapping a part writes `s=N` into the address bar, so a copied link opens on that part.
- **`&mark=1`:** owner mode for marking parts. See "Adding a new MV".
- **Opened from disk** (fetch fails): plays the built-in `FALLBACK` in `index.html`. Keep its `video` URL current.

## `mvs/<slug>.json`

```jsonc
{
  "slug": "yixiangtiankai",          // lowercase pinyin; also the R2 folder name
  "title": "异想天开",               // "titleEn": add only once an OFFICIAL English title exists — never a pinyin guess
  "artist": "肖战", "artistEn": "Xiao Zhan",
  "released": "2026-10-04", "bpm": 119,
  "video":  "https://assets.xz-studio-gallery.com/dance/<slug>/practice_1080p.mp4",
  "poster": "https://assets.xz-studio-gallery.com/dance/<slug>/poster.jpg",
  "sources": [{"label": "肖战微博", "labelEn": "Weibo", "url": "…"}],   // "open the original" chips
  "douyinEmbed": {"vid": "<numeric id>", "by": "肖战工作室"},          // optional; omit = links only
  "sections": [{"name": "第1段", "en": "Part 1", "start": 4.6, "end": 19.8}],   // times in the PRACTICE CUT
  "build": {                                     // input for make_cut.py
    "original": "https://assets.xz-studio-gallery.com/full/….mp4",
    "lead": 3.0, "tail": 1.5, "card": 1.6, "posterAt": 112,
    "sections": [{"name": "第1段", "en": "Part 1", "start": 49.8, "end": 65}]   // times in the ORIGINAL MV
  }
}
```

`sections` (practice-cut times) is written by `make_cut.py --upload`. You only edit `build.sections` by hand.

## Adding a new MV

1. **Find the full MV in R2.** Autosync usually stores it under `full/`. Create `mvs/<slug>.json` with the metadata, sources and `douyinEmbed`, and temporarily set `"video"` to the original MV URL.
2. **Measure the tempo.** Run `python tools/bpm.py <original url>` and put the result in `"bpm"`.
3. **Mark the dance parts.** Open `?mv=<slug>&mark=1`. For each part, set A and B, name it 第N段 / Part N and save. Then use "复制段落数据" to copy the data. Paste the copied `sections` into `build.sections`; those times are in the original MV.
   - The draft lives in localStorage `xzdance.markDraft.<slug>`. That is per browser, so mark on one device.
4. **Pick a poster frame.** Choose a frame time for `build.posterAt`. This is in seconds of the *practice cut*.
5. **Build and check without uploading.** Run `python tools/make_cut.py <slug>`. Look at the cards and verify the output.
6. **Upload.** Run `python tools/make_cut.py <slug> --upload`. This uploads to `dance/<slug>/` and re-downloads from the CDN to compare. Add `--replace` to overwrite an existing cut. It also rewrites `video`, `poster` and `sections`, and the catalog entry (each with a `.bak`).
7. **Preview and push.** With 2+ MVs, the home page switches to the catalog automatically.

## Practice cut: why it's built this way

- **Why a cut at all:** fans only download the dance (~53 MB at 1080p, versus the full MV), and the copyright/credit is burned in.
  - Each part is introduced by a bilingual chapter card.
  - The corner text reads "MV 版权归原作者 · 仅供练舞 · 请勿转载" / "© Original MV · practice use only".
- **Frame snapping:** every cut point is snapped to a whole frame (25 fps), and the card lasts 40 frames. Without this, the audio drifts a little further after every part (+20/+60/+80 ms was measured).
- **Verify step:** the build refuses to upload unless audio is within 40 ms and the frame NCC is at least 0.7 at the start, middle and end of each part.
- **Python CDN checks:** Cloudflare returns 403 to Python's default urllib user-agent, so send a browser UA.

## R2 and the other tools

- **Bucket:** `xzstudiogallery` (CDN `assets.xz-studio-gallery.com`), prefix `dance/<slug>/`.
- **No credentials in this repo.** The tools read env vars `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET`, or parse autosync's `app.py` on this PC.
- **Autosync orphan check:** it skips `dance/` (`_excluded_prefixes` in autosync `app.py`), so these files are never flagged as orphans. Keep it that way.
- **Old object:** `dance/yxtk_practice_1080p.mp4` (the first cut, whose cards said "Section N") was deleted from R2 on 2026-10-06. A local copy is in `_backup/r2/`.

## Page behaviour worth knowing

- **Speed:** `playbackRate` with `preservesPitch`.
- **Count-in:** one beat lasts `60000 / bpm / rate` ms. The loop watcher runs on rAF, not `timeupdate`.
- **iOS needs a tap to start media.** `primeMedia()` starts the video and holds it on the first tap, so the delayed `play()` after the count-in is allowed.
- **Fullscreen:** uses the Fullscreen API where possible.
  - If a request hasn't settled after 0.8 s (WeChat and other in-app browsers), or on iPhone, the page falls back to filling the browser window. This keeps the count-in and mirror visible.
- **Douyin embed** (`open.douyin.com/player/video?vid=`): only loaded after a tap. It has speed controls but no API the parent page can use.
  - A random bubble line points to it.
  - After 10 minutes of actual practice, a nudge appears once per visit.
- **Weibo videos** can't be embedded officially (see `Platform API Reference/WEIBO_API_GUIDE.md` §18). Link to them instead.
- **Names:** the header is always the site name, "XZ · 舞蹈练习室 DANCE WITH XIAO ZHAN". The line under it names the MV ("异想天开 · MV 练习版", plus `titleEn` once it exists). Browser tab: "XZ Dance Room · XZ 舞蹈练习室" on the catalog, and "<title> · XZ 舞蹈练习室" on an MV page, so bookmarks and share previews say which MV it is.
- **Layout, top to bottom:** a short help box, the player, the timeline, a one-line row of part tabs (所有段落 All parts + 第N段; tapping the current part restarts it, 所有段落 stops looping; the row scrolls sideways if there are many parts), then one row with Play and the speed buttons (the 3-second skip buttons were removed on request; the ← → keys still skip 3 s). The source-link chips are labelled "喜欢就去原视频点赞、转发 ❤ Like & share the original". The footer holds the links to XZWorks and XZYT (`.pages.dev` URLs), "© 2026 CanadaXFX. All rights reserved." and a folded 使用条款 Terms of Use (`<details>`, no JS; 7 bilingual lines adapted from the galleries' terms, plus "practice videos: watch here only, no download, re-upload or embed"). There is no separate MV-copyright line on the page (Terms line 1 and the text burned into the video cover it), so MV files have no `copyright` field.
- **Viewer preferences** (speed, loop, mirror, count-in) are stored in localStorage `xzdance.*`. They are shared across MVs and are per viewer only.
