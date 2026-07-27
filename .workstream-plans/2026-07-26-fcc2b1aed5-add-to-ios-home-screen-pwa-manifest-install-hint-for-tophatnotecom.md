---
id: 2026-07-26-fcc2b1aed5
title: Add to iOS Home Screen (PWA manifest + install hint) for top.hatnote.com
status: implemented
workstream: top
repo: top
created: 2026-07-26
updated: 2026-07-27
tabled_note: ''
---

# Add to iOS Home Screen (PWA manifest + install hint) for top.hatnote.com

## Context

`top.hatnote.com` has no web app manifest, no icons (not even a favicon), and no home-screen affordance. Goal: make the site installable as a standalone iOS home-screen app (own icon, no browser chrome, launches to the current day's chart), and show a dismissible in-page hint telling iOS visitors how to do it — Brave for iOS has no "Add to Home Screen" at all (confirmed: third-party iOS browsers except Chrome have not implemented it), so the hint must name Safari explicitly.

End state: `/manifest.json` + icon PNGs served from `static/`, manifest/apple-touch-icon/`apple-mobile-web-app-*` tags in every generated page's `<head>`, a one-time bottom banner on chart pages for non-standalone iOS visitors, deployed and verified on a real iPhone.

## Key repo facts (verified this session)

- Pages are rendered by `top/build_page.py` from ashes/dust templates. `top/templates/base/*.dust` are the sources; `top/l10nize.py --lang X` substitutes `$string$` placeholders from `top/templates/strings/X_strings.yaml` and writes `top/templates/X_<name>.dust`. `choose_template()` (`build_page.py:57`) prefers `<lang>_<tmpl>` and falls back to the un-prefixed one.
- Localized template sets that exist today (11): `ar en fa fi gl hu no or pa sv ur` (`pt_strings.yaml` exists but has no generated templates — do NOT run l10nize for `pt`, it would create 7 new untracked templates).
- `base/chart.dust` renders three depths of the same page: dated page (`dir_depth = '../'*4`), `/<lang>/index.html` (`'../'`), and root `/index.html` (`''`) — see `save_chart()` in `build_page.py:166-222`. All asset hrefs use `{dir_depth}`.
- `about.dust` is a single non-localized template at site root; it uses plain relative hrefs (`css/fonts.css`), no `dir_depth`.
- **`.gitignore` contains `static/`** — the 29 tracked files under `static/` were force-added. New static assets MUST be added with `git add -f`.
- nginx (`conf/top.nginx.conf`) serves `/home/hatnote/top/static/` with `expires 1h`; no custom `types` block, so `.json` gets `application/json` from nginx's default mime.types (reason to use `manifest.json`, not `manifest.webmanifest`, which is absent from older nginx mime.types).
- Colors in use: `#0d0f05` (dark bar / existing `theme-color`), `#fbfbfb` (`.top-area` background, near-white), `#0098d8` (link blue), `#dfe0e2` (body background).
- `static/js/top.js` is a vanilla IIFE with `DOMContentLoaded` init calls; only `chart.dust` loads it. `static/fonts/lato-v11-latin-900.ttf` is the display face (`h1 .ultra { font-weight: 900 }`).
- Local build works: `./.venv/bin/python` (3.14.5) has all deps; local data exists for `2026/7/10` in `en` and `ar`, so `build_page.py --date 20260710 --lang en` regenerates the dated page, `/en/index.html`, and root `/index.html`.
- ImageMagick 7 (`magick`) is on the laptop; Pillow is NOT installed and MUST NOT be added to `requirements.txt` — icons are generated once locally and committed as PNGs.

## Approach

Steps 1–3 are independent; step 4 depends on 3; steps 5–6 are independent of everything else. Step 7 (deploy) is last.

### 1. Generate and commit icons

Run from the repo root (`magick` = ImageMagick 7). Design: near-black `#0d0f05` field, "TOP" in white Lato Black above "100" in `#0098d8`.

```bash
F=static/fonts/lato-v11-latin-900.ttf
magick -size 512x512 xc:'#0d0f05' -font $F \
  -fill '#fbfbfb' -pointsize 78  -gravity center -annotate +0-96 'TOP' \
  -fill '#0098d8' -pointsize 200 -gravity center -annotate +0+40 '100' \
  static/img/icon-512.png
magick static/img/icon-512.png -resize 192x192 static/img/icon-192.png
magick static/img/icon-512.png -resize 60% -background '#0d0f05' -gravity center -extent 512x512 \
  static/img/icon-maskable-512.png
magick static/img/icon-512.png -resize 180x180 -background '#0d0f05' -alpha remove -alpha off \
  static/img/apple-touch-icon.png
git add -f static/img/icon-512.png static/img/icon-192.png static/img/icon-maskable-512.png static/img/apple-touch-icon.png
```

`apple-touch-icon.png` must be opaque (iOS composites transparency onto black and shows artifacts) — hence `-alpha remove -alpha off`. The maskable variant is a separate file with 20% padding rather than a dual-purpose `"any maskable"` declaration, so Android's circular mask never clips the "TOP".

### 2. Create `static/manifest.json`

Exact contents (relative-to-root URLs; the file always lives at `/manifest.json`):

```json
{
  "id": "/",
  "name": "Wikipedia Top 100",
  "short_name": "Top 100",
  "description": "The most-visited Wikipedia articles, updated daily.",
  "lang": "en",
  "dir": "ltr",
  "start_url": "/?src=homescreen",
  "scope": "/",
  "display": "standalone",
  "background_color": "#dfe0e2",
  "theme_color": "#0d0f05",
  "icons": [
    {"src": "/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/img/icon-512.png", "sizes": "512x512", "type": "image/png"},
    {"src": "/img/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
```

`start_url` keeps `?src=homescreen` so the existing GA4 tag distinguishes app launches; `scope: "/"` covers every language and archive path so in-app navigation never kicks out to the browser. Commit with `git add -f static/manifest.json`.

### 3. Add the head block to the base templates

Insert this block verbatim (7 lines, 4-space indent to match) into `top/templates/base/chart.dust` immediately after the `theme-color` meta (currently line 6):

```html
    <link rel="manifest" href="{dir_depth}manifest.json">
    <link rel="apple-touch-icon" href="{dir_depth}img/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="192x192" href="{dir_depth}img/icon-192.png">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Top 100">
```

`status-bar-style: default` (not `black-translucent`) because `.top-area` is `#fbfbfb`: the status bar area picks up the light page background with dark text and needs no `env(safe-area-inset-top)` padding.

Add the same block plus `<meta name="theme-color" content="#0d0f05">` (these four templates lack it) after the `viewport` meta in:
`base/index.dust`, `base/month_index.dust`, `base/year_index.dust`, `base/project_index.dust`.

In `top/templates/about.dust` (root-level, no `dir_depth`) add the same block with `{dir_depth}` stripped — `href="manifest.json"`, `href="img/apple-touch-icon.png"`, `href="img/icon-192.png"` — plus the `theme-color` meta, after the viewport line (line 5).

Also in `base/chart.dust`, change the blog nav link (line 36) to
`<li><a href="https://blog.hatnote.com/" target="_blank" rel="noopener">$blog_link$</a></li>`:
in iOS standalone mode there is no back button, so an in-app navigation to blog.hatnote.com traps the user. (Leave `base/index.dust`'s blog link alone — it is `href="#"`, a pre-existing unrelated bug.)

### 4. Regenerate the localized templates

```bash
for L in ar en fa fi gl hu no or pa sv ur; do ./.venv/bin/python top/l10nize.py --lang $L; done
```

Expect no "could not find substitutions" output (the new markup contains no `$string$` placeholders). Verify: `grep -L 'rel="manifest"' top/templates/*_chart.dust top/templates/*_index.dust` prints nothing.

### 5. Install-hint banner in `static/js/top.js`

Add one function, called from the existing `DOMContentLoaded` handler alongside `initSparklines()` / `initCoverFallback()` / `initKeyNav()`. Vanilla, no jQuery, matching the file's existing style.

Display conditions — ALL must hold:
- iOS/iPadOS: `/iP(hone|od|ad)/.test(navigator.platform) || (navigator.maxTouchPoints > 1 && /Mac/.test(navigator.userAgent) && 'ontouchend' in document)`
- not already installed: `!(navigator.standalone || window.matchMedia('(display-mode: standalone)').matches)`
- not dismissed: `localStorage.getItem('a2hs-dismissed') !== '1'`, wrapped in `try/catch` (Private Browsing throws on access)
- English page: `(document.documentElement.lang || 'en').slice(0, 2) === 'en'` — the copy is English-only and the site is localized into 11 languages; a non-English page shows nothing rather than stray English.

Markup built in JS and appended to `document.body`:

```html
<div class="a2hs">
  <p>Add <b>Top 100</b> to your Home Screen: in <b>Safari</b>, tap Share then &ldquo;Add to Home Screen.&rdquo; (Brave and Firefox for iOS can&rsquo;t do this.)</p>
  <button type="button" class="a2hs-close" aria-label="Dismiss">Got it</button>
</div>
```

Clicking `.a2hs-close` removes the element and writes `localStorage['a2hs-dismissed'] = '1'` (inside `try/catch`; if storage throws, still remove the element for the session).

### 6. Banner styles in `static/css/chart.css`

Append at end of file (the file has no media-query section to slot into; existing mobile rules are inline `@media (max-width: …)` blocks):

```css
.a2hs {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.75em;
  padding: 0.75em 1em calc(0.75em + env(safe-area-inset-bottom));
  background: #0d0f05;
  color: #fbfbfb;
  font-size: 0.95em;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.25);
}
.a2hs p { margin: 0; flex: 1; }
.a2hs-close {
  flex: none;
  font-family: inherit;
  font-size: 0.95em;
  font-weight: 900;
  color: #0d0f05;
  background: #fbfbfb;
  border: 0;
  border-radius: 7px;
  padding: 0.5em 0.9em;
}
```

### 7. Ship it

```bash
git add -f static/manifest.json static/img/icon-*.png static/img/apple-touch-icon.png
git add static/js/top.js static/css/chart.css top/templates
git commit -m "PWA: manifest, home-screen icons, iOS add-to-home-screen hint"
git push origin master
```

Deploy to wenli — see **Deployment** below.

## Critical files & anchors

- `top/templates/base/chart.dust` — `<head>` lines 4–21 (asset links use `{dir_depth}`), nav `<li>` blog link line 36. The only template that renders `/`, `/en/`, and dated pages.
- `top/build_page.py:166-222` (`save_chart`) — where `dir_depth` is set to `''`, `'../'`, `'../'*4`; explains why the head block must use `{dir_depth}` and the manifest must not.
- `top/l10nize.py` — regeneration step; silently leaves `$name$` literals in output if a string is missing, so watch its stdout.
- `static/js/top.js` — IIFE + `DOMContentLoaded` block at the bottom; add the banner init there.
- `.gitignore` (`static/`) — every new static asset needs `git add -f` or it silently never ships.

## Verification

Local, from repo root:

1. Regenerate and confirm the tags land at all three depths:
   ```bash
   ./.venv/bin/python top/build_page.py --date 20260710 --lang en --project wikipedia
   grep -c 'rel="manifest"' static/index.html static/en/index.html static/en/wikipedia/2026/7/10.html
   ```
   → `1` for each file. Also `grep -o 'href="[^"]*manifest.json"' static/en/wikipedia/2026/7/10.html` → `href="../../../../manifest.json"` (root index → `href="manifest.json"`).
2. Non-English page unaffected but still tagged: `./.venv/bin/python top/build_page.py --date 20260710 --lang ar --project wikipedia && grep -c 'rel="manifest"' static/ar/index.html` → `1`.
3. Manifest + icons serve correctly:
   ```bash
   cd static && python3 -m http.server 8765 &
   curl -sI localhost:8765/manifest.json | head -3          # 200, Content-Type: application/json
   python3 -m json.tool < manifest.json > /dev/null && echo JSON_OK
   for f in icon-192 icon-512 icon-maskable-512 apple-touch-icon; do magick identify static/img/$f.png; done
   ```
   → sizes 192x192, 512x512, 512x512, 180x180; apple-touch-icon reports no alpha channel.
4. Banner behavior (browser tool against `http://localhost:8765/`):
   - iPhone UA + touch emulation → banner visible at bottom, text mentions Safari; click "Got it" → element gone, `localStorage['a2hs-dismissed'] === '1'`; reload → still gone.
   - desktop UA → banner absent.
   - iPhone UA + `page.emulateMediaFeatures([{name:'display-mode', value:'standalone'}])` → banner absent (simulates the installed app).
   - `/ar/` page with iPhone UA → banner absent (non-English gate).
5. Device proof (after deploy), the acceptance test: on the iPhone open `https://top.hatnote.com` **in Safari** → banner appears → Share → "Add to Home Screen" → the suggested name is "Top 100" and the icon is the TOP/100 tile → launch from the home screen → opens with no Safari address bar (standalone), lands on the current day's chart, and the banner does not appear.

## Deployment

Additive, low risk: new static files go live on `git pull`; the `<head>` tags appear once pages are re-rendered. Root `/index.html` and `/<lang>/index.html` are rebuilt by the nightly 21:00 cron anyway, so a pull plus one manual `en` rebuild makes it usable immediately.

1. Check whether sudo is needed: `ssh wenli 'ls -ld /home/hatnote/top /home/hatnote/top/.git /home/hatnote/top/static'`. `mahmoud` is in group `hatnote`; if the repo and `static/` are group-writable, run steps 2–3 directly as `mahmoud`, no sudo.
2. If not group-writable, ask the user to grant temporary passwordless sudo (the convention from the previous deploy):
   ```bash
   echo 'mahmoud ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/99-deploy-tmp && sudo chmod 440 /etc/sudoers.d/99-deploy-tmp && sudo visudo -c
   ```
   Verify with `ssh wenli 'sudo -n true && echo SUDO_OK'` before proceeding, and tell the user to `sudo rm /etc/sudoers.d/99-deploy-tmp` at the end (verify it fails afterwards).
3. Pull and rebuild the most recent complete `en` chart (prefix each command with `sudo -n -H -u hatnote bash -lc '…'` if step 1 said sudo is needed):
   ```bash
   cd /home/hatnote/top && git pull origin master        # falls back to https://github.com/hatnote/top.git master if the SSH key is unverified
   cd /home/hatnote/top/top && D=$(/home/hatnote/virtualenvs/top3/bin/python -c \
     "import build_page; print(build_page.check_most_recent().strftime('%Y%m%d'))") && \
     /home/hatnote/virtualenvs/top3/bin/python build_page.py --date $D --lang en --project wikipedia
   ```
   Do not invent the date from a laptop clock — `check_most_recent()` reads what is actually on disk. If a nightly poller is running (`ps aux | grep get_data.py`), the rebuild is still safe: it only re-renders already-fetched data.
4. Verify live:
   ```bash
   curl -sI https://top.hatnote.com/manifest.json | head -3      # 200 application/json
   curl -sI https://top.hatnote.com/img/apple-touch-icon.png | head -2
   curl -s https://top.hatnote.com/ | grep -c 'rel="manifest"'   # 1
   ```
   Then run verification step 5 on the phone.

Archived dated pages (~70k) keep their old `<head>` until regenerated; `top/retrofit_pages.py` exists for bulk head injection but is deliberately not used here — the home-screen app launches at `/`, and `scope: "/"` keeps navigation into archives inside the installed app regardless.

## Assumptions & contingencies

- **Icon art**: "TOP" over blue "100" on near-black. If it reads poorly at home-screen size, the fallback is the same command without the "TOP" line (`-fill '#fbfbfb' -pointsize 210 -annotate +0+0 '100'`).
- **No service worker.** iOS Add to Home Screen does not need one, and a stale-content cache on a site whose whole point is "today's chart" is a real hazard. Consequence: Chrome/Edge on Android and desktop will NOT fire `beforeinstallprompt`, so no native install button there. If Android installability is wanted later, add a network-first service worker with an offline fallback page — do not add a cache-first one.
- **Banner copy is English-only and only shows on English pages.** If localized copy is wanted, add an `$add_to_home_hint$` string to all 12 `templates/strings/*_strings.yaml`, render the banner markup (hidden by default) in `base/chart.dust`, and have `top.js` unhide it instead of building the DOM — do not leave an untranslated `$add_to_home_hint$` literal in a localized template.
- **iOS 26 note**: on iOS 26 every home-screen bookmark opens as a web app by default, so `display: standalone` is belt-and-braces there; it still matters on iOS 18 and earlier.
