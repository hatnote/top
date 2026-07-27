---
id: 2026-07-11-d6722f7e16
title: top.hatnote.com — mobile readability + machine readability
status: implemented
workstream: top
repo: top
created: 2026-07-11
updated: 2026-07-11
tabled_note: ''
---

# top.hatnote.com — mobile readability + machine readability

## Context

top.hatnote.com renders unusably on phones and is nearly invisible to crawlers/agents. Measured on the live site (headless Chrome, 390×844): no `<meta name="viewport">` + `.container { min-width: 500px }` clips content (document scrollWidth 535px vs 390px viewport), no doctype (quirks mode), 7.4 MB transfer of which 7.2 MB is 95 eagerly-loaded 500px cover images injected as CSS `background`, and 256 KB of render-blocking 2013-era jQuery. Machine-side: per-day JSON is already published (`/{lang}/{project}/{Y}/{M}/{D}.json`) but undiscoverable; the live RSS channel title renders as "` Wikipedia Top 100`" because the deployed `en_rss.xml` references `{full_lang}`/`{site.lang_code}` which are not in `update_feeds`' context; `robots.txt` 404s; there is no canonical, OG, JSON-LD, `<html lang>`, or meta description. End state: responsive pages (new + retrofitted archive), lazy-loaded images, no jQuery on new pages, valid discoverable feeds, structured data, and agent-facing docs (`llms.txt`).

User decisions already made: retrofit archives with viewport meta (yes), replace jQuery with vanilla JS (yes), swap dead UA analytics for GA4 gtag (yes).

## Architecture constraints (read first)

- **Python 2 only.** `top/*.py` uses `print` statements, `email.Utils`, `str.decode`. Do NOT port to py3. All script runs happen in Docker: `docker run --rm --platform linux/amd64 -v "$PWD":/app -w /app python:2.7 bash -c "pip install -q ashes boltons Babel==2.2.0 PyYAML==3.11 python-dateutil==2.4.2 && <cmd>"`.
- **Two template flavors, both must be edited:**
  - `top/templates/base/*.dust|xml|html` — l10n sources. `top/l10nize.py --lang <L>` substitutes `$key$` placeholders from `top/templates/strings/<L>_strings.yaml` and overwrites `top/templates/<L>_<name>`. Regenerate for: `ar en fa fi gl hu no or pa sv ur` (11 langs). Skip `pt` (strings exist, templates were never generated, lang not in `update_all.sh`).
  - Root fallbacks `top/templates/chart.dust`, `rss.xml`, `summary.html`, `index.dust`, `month_index.dust`, `year_index.dust`, `project_index.dust` — used via `choose_template()` (`top/build_page.py:55`) by every lang WITHOUT per-lang templates (de, fr, ko, es, zh, …). These use dynamic dust vars (`{full_lang}`) instead of baked strings; mirror each edit manually.
- **Hand-patch hazard:** `ar_chart.dust`, and (verify with `grep -l 'dir=rtl' top/templates/*_chart.dust`) `fa_chart.dust`/`ur_chart.dust`, carry a manual `<body dir=rtl>` that regeneration destroys. Step 6 replaces it with a `$html_dir$` strings key BEFORE regenerating. After every regen, review `git diff top/templates/` — any other disappearing manual patch must be ported into `base/` or the strings yaml first, then regen again.
- **Shared CSS is retroactive.** `static/css/chart.css` is loaded by ~70k archived pages. Never change existing selectors' layout mode; new layout rules are scoped under the new `.chart` class that only new markup carries (fallback pre-decided: if any global rule breaks the 2016 fixture in verification, move it under `.chart`).
- Old jQuery files (`static/js/jquery*.js`) stay on disk forever — archived pages reference them. Do not delete.

## Approach

### Step 1 — HTTPS cutover in `top/common.py` (independent)

Lines 16–20: change `http://top.hatnote.com` → `https://top.hatnote.com` in `LANG_PROJ_LINK_TMPL`, `DATE_PERMALINK_TMPL`, `PERMALINK_TMPL`. No other code matches `http://` in `top/*.py`. Side effect (accepted): RSS `<guid>` scheme changes, so feed readers re-show up to 10 entries once.

### Step 2 — Responsive + lazy-image CSS in `static/css/chart.css` (independent)

1. `.container` (line 146): delete `min-width: 500px;` — this is the archive-wide mobile fix once viewport meta exists. Keep `max-width: 800px`.
2. Keep `.row { display: table }` and `.column { display: table-cell }` untouched (archived pages). Append new scoped block after the `.column` rule:
   ```css
   .chart { list-style: none; margin: 1em 0; }
   .chart .row { display: flex; overflow: hidden; }
   .chart .column { display: block; }
   .chart .rank { display: flex; flex: none; align-items: center; justify-content: center; box-sizing: content-box; }
   .chart .cover-art { flex: none; position: relative; }
   .chart .label { flex: 1; min-width: 0; }
   .cover-art img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
   .chart .row:hover .permalink { display: inline; }
   ```
   (`.rank` keeps its existing `width: 50px`/padding; flex items honor `width` with `flex-basis: auto`.)
3. Replace the near-empty `@media (max-width: 800px)` block (lines 60–71) body — keep `.ultra { display: block }` and `.container { padding: 0 1em }`, delete the empty `body {}` — and add a second breakpoint:
   ```css
   @media (max-width: 640px) {
     h1 { font-size: 2.25em; }
     .subtitle { font-size: 1.15em; }
     .rank { width: 2em; font-size: 1.4em; padding: 0.2em 0.1em; }
     .cover-art { width: 96px; }
     .title { font-size: 1.4em; }
     .summary { font-size: 0.95em; }
     .streak { padding-left: 0.5em; }
     .ext-icon { margin: 0.35em; }
   }
   ```
   These `width` overrides intentionally hit BOTH old table-cells and new flex items.

### Step 3 — Vanilla JS: new `static/js/top.js` (independent)

Create the file (no existing equivalent found; replaces jquery+peity+jknav+hotkeys for new pages only). Plain ES5-compatible, wrapped in an IIFE, run on `DOMContentLoaded`:
- **Sparklines:** for each `span.sparkline`, parse `textContent.split(',')` → numbers; build an inline `<svg class="peity" width="50" height="14">` with one `<polyline>` (points scaled to min/max of the series, `fill="none"`, `stroke="rgba(116,131,138,0.7)"`, `stroke-width="1"`); insert via `span.insertAdjacentElement('afterend', svg)` (span stays `display:none` via existing CSS). Empty/NaN series → skip element, no throw.
- **j/k navigation:** `keydown` listener on `document`; ignore events with `event.metaKey||event.ctrlKey||event.altKey`; `j` = scroll to next `li.row`, `k` = previous, tracked by index, `row.scrollIntoView({behavior:'smooth', block:'start'})`. Bounds clamp, no wrap.
- **Permalink hover** is handled by the CSS rule from Step 2 — no JS.
No jQuery, no globals beyond the IIFE.

### Step 4 — Build context additions in `top/build_page.py` (before Steps 5–6 verification)

1. Imports: extend the `from common import (...)` block (lines 21–28) with `DATE_PERMALINK_TMPL` and `FEED_FILE_TMPL`; change line 6 to `from json import load, dumps`.
2. New module-level helper above `save_chart`:
   ```python
   def make_jsonld(data):
       items = [{'@type': 'ListItem',
                 'position': a['rank'],
                 'url': a['url'],
                 'name': a['title']} for a in data.get('articles', [])]
       doc = {'@context': 'https://schema.org',
              '@type': 'ItemList',
              'url': data['canonical_url'],
              'numberOfItems': len(items),
              'itemListOrder': 'https://schema.org/ItemListOrderAscending',
              'itemListElement': items}
       return dumps(doc).replace('</', '<\\/')
   ```
3. In `save_chart` after `data.setdefault('meta', ...)` (line 177), add:
   ```python
   data['canonical_url'] = DATE_PERMALINK_TMPL.format(
       lang=lang, project=project, year=query_date.year,
       month=query_date.month, day=query_date.day)
   data['current_json'] = data['current'][:-len('.html')] + '.json'
   if data.get('articles'):
       data['og_image'] = data['articles'][0]['image_url']
   data['jsonld'] = make_jsonld(data)
   ```
   The index renders (lines 187–199) reuse the same dict, so index pages get a canonical pointing at the dated page — intended dedup.
4. In `update_feeds` `render_ctx` (lines 231–235), add key
   `'feed_url': 'https://top.hatnote.com/' + FEED_FILE_TMPL.format(lang=lang, project=project),`
   and inside the entry loop, after the `date_i_data['summary'] = ...` line:
   ```python
   if date_i_data.get('articles'):
       date_i_data['og_image'] = date_i_data['articles'][0]['image_url']
   ```

### Step 5 — Chart template overhaul: `top/templates/base/chart.dust` + root `chart.dust` (depends on Steps 3–4)

`base/chart.dust` edits (root `chart.dust` mirrors every item; substitutions for root noted in parens):

**Head** — replace lines 1–10 region so the document becomes:
```html
<!DOCTYPE html>
<html lang="{lang}"$html_dir$>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#0d0f05">
    <title>{?is_index}$index_title${:else}$full_title${/is_index}</title>
    <meta name="description" content="$alt_tagline$">
    <link rel="canonical" href="{canonical_url}">
    <meta property="og:site_name" content="Hatnote Top 100">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{?is_index}$index_title${:else}$full_title${/is_index}">
    <meta property="og:description" content="$alt_tagline$">
    <meta property="og:url" content="{canonical_url}">
    {?og_image}<meta property="og:image" content="{og_image}">{/og_image}
    <meta name="twitter:card" content="summary">
    <link href="{dir_depth}css/fonts.css" rel="stylesheet" type="text/css">
    <link href="{dir_depth}css/chart.css" rel="stylesheet" type="text/css">
    <link href="{dir_depth}feeds/{lang}{project_lower}.rss" title="$language_project$ $title$" type="application/rss+xml" rel="alternate">
    <link href="{dir_depth}{current_json}" type="application/json" rel="alternate">
    <script defer src="{dir_depth}js/top.js"></script>
```
(Root `chart.dust`: no `$html_dir$` — all fallback langs are LTR, use `<html lang="{lang}">`; title stays but fix its existing bug to `{full_lang} {project} Top 100{^is_index} on {formatted_date}{/is_index}`; og:title same expression; description literal `The most-visited {full_lang} {project} articles, updated daily.`; rss link title `{full_lang} {project} Feed` with the RELATIVE href `{dir_depth}feeds/...` replacing the current absolute `http://top.hatnote.com/...`.)

- Delete the four jquery `<script src>` lines and the whole inline `$(function(){...})` script.
- Keep the inline `{#articles}.cover-{rank}{...}{/articles}` `<style>` block DELETED in base and root — new pages use real `<img>` (below). This drops ~100 inline style rules per page.
- After the `<!-- Generated ... -->` comment, add before `</head>`:
  `<script type="application/ld+json">{jsonld|s}</script>`

**Body:**
- Chart list: `<ul>` → `<ol class="chart">` (both the open tag at base line 64 and its `</ul>`).
- Cover cell (base line 70): `<a class="column cover-art cover-{rank}" href="{url}" target="_blank"></a>` →
  ```html
  <a class="column cover-art" href="{url}" target="_blank" rel="noopener"><img src="{image_url}" alt="{title}" loading="lazy" decoding="async"></a>
  ```
- Add `rel="noopener"` to every remaining `target="_blank"` anchor (title link, Google search, Google News; root also: twitter-era links — replace root's twitter share block with base's two ext-icon links, using `&hl={lang}`).
- `<body dir=rtl>` never appears in base; RTL now comes from `$html_dir$` (Step 6).
- Blog links: `http://blog.hatnote.com` → `https://blog.hatnote.com` (base line 48, root line 47).
- Replace the trailing UA analytics `<script>` block with:
  ```html
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-9LD7M2WME2"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-9LD7M2WME2');</script>
  ```
- Close with `</body></html>` as before.

**Index-family templates** (`base/index.dust`, `base/month_index.dust`, `base/year_index.dust`, `base/project_index.dust`, root equivalents, and `about.dust`): light treatment only — add `<!DOCTYPE html>`, viewport meta, and swap the UA snippet for the gtag snippet above; in `about.dust` also `<html lang="en">` and drop its unused `js/jquery.js` script tag. Do NOT add lang attributes to index-family templates (their render contexts don't reliably carry `lang`). Also fix root `index.dust`'s stray `</table>` (line 59) → delete it.

### Step 6 — RTL strings key + RSS templates + regeneration (depends on Step 5)

1. Add `html_dir` to all 12 strings yamls (`top/templates/strings/*_strings.yaml`):
   - `ar`, `fa`, `ur`: `html_dir: ' dir="rtl"'`
   - `en`, `fi`, `gl`, `hu`, `no`, `or`, `pa`, `pt`, `sv`: `html_dir: ''`
2. `top/templates/base/rss.xml`:
   - Line 2: `xml:lang="{site.lang_code}"` → `xml:lang="{lang_code}"`; add namespace `xmlns:atom="http://www.w3.org/2005/Atom"`.
   - After the `<link>` line add: `<atom:link href="{feed_url}" rel="self" type="application/rss+xml"/>`.
   - Delete the `<copyright>{copyright}</copyright>` line (var never supplied) and the `<!-- TODO ... image ... -->` comment block and the `<!-- TODO -->` on the generator line.
   - Inside `<item>`, after `<link>`: `{?og_image}<media:thumbnail url="{og_image}" width="500"/>{/og_image}`.
   - Mirror all of the above into root `templates/rss.xml`, which additionally keeps its `{lang_name}`-based title/description (those ARE in `update_feeds` ctx — verified `build_page.py:231-235`).
3. Regenerate per-lang templates (fixes the live broken `en_rss.xml` which still references `{full_lang}`):
   `for L in ar en fa fi gl hu no or pa sv ur; do <docker py2> python top/l10nize.py --lang $L; done`
   - Watch stdout for `could not find substitutions for [...]` warnings. If a lang's yaml lacks `rss_title` or `alt_tagline`: add `rss_title:` = that yaml's `index_title` value and `alt_tagline:` = its `tagline` value with HTML tags stripped. Re-run.
   - `git diff top/templates/` must show only: new head/body from Step 5, `dir="rtl"` moved from `<body>` to `<html>` for ar/fa/ur, and the rss.xml fixes. Anything else disappearing = a manual patch; port it to `base/` or strings, regen again.

### Step 7 — Crawler/agent files (independent)

1. Create `static/robots.txt`:
   ```
   User-agent: *
   Allow: /
   ```
   (Decision: no sitemap — URLs are fully discoverable through the month/year archive index pages and the predictable `/{lang}/{project}/{Y}/{M}/{D}.html` scheme; a 70k-URL sitemap adds build complexity for negligible gain.)
2. Create `static/llms.txt` (markdown), content:
   - H1 `Hatnote Top 100` + one-line summary (most-visited Wikipedia articles per language, updated daily ~02:00 UTC).
   - URL patterns section: HTML `https://top.hatnote.com/{lang}/{project}/{year}/{month}/{day}.html` (month/day NOT zero-padded), JSON same path with `.json`, RSS `https://top.hatnote.com/feeds/{lang}{project}.rss`, archive indexes at `/{lang}/{project}/{year}/{month}/`, language list at `/about.html`.
   - JSON field glossary: `articles[]` with `article`, `title`, `url`, `rank`, `views` (int), `views_short`, `view_delta`, `view_trend` (HTML arrow entity), `streak_len`, `history` (last 10 days of views, zeros = off-chart), `image_url`, `summary`, `permalink`.
   - Note: data source is the Wikimedia Pageviews API; repo `https://github.com/hatnote/top`.
3. `top/templates/about.dust`: add an English `<h2>Data &amp; feeds</h2>` section after the RSS Feeds block documenting the same JSON/RSS URL patterns in one short paragraph with a code-formatted example link to `/en/wikipedia/2026/7/10.json`, plus `/llms.txt`. Give about.dust the Step 5 light-head treatment here too.

### Step 8 — Archive retrofit script: new `top/retrofit_pages.py` (independent; run on server)

New script, py2-compatible, stdlib only (no existing equivalent found):
- Walks `BASE_PATH` (import from `common`) via `os.walk`, collecting `*.html` files; skips `js/`, `css/`, `img/`, `fonts/` dirs.
- Per file (binary read): if `b'name="viewport"'` present → skip (idempotency). Else insert `b'\n    <meta name="viewport" content="width=device-width, initial-scale=1">'` immediately after the first `b'<meta charset="UTF-8">'`; if that anchor is missing, insert after the first `b'<head>'`; if neither exists, count as skipped-no-anchor and report the path.
- Writes to `path + '.tmp'` then `os.rename` (atomic). Preserves everything else byte-for-byte.
- CLI: default = dry-run printing counts (`would modify N, already ok M, no anchor K`) and up to 20 sample paths; `--apply` performs writes. `--root <dir>` overrides BASE_PATH (needed for fixture testing).
- Deployment: on the server, after `git pull`, run once: `<venv python> top/retrofit_pages.py` (review counts) then `--apply`. Do not add to cron — new pages already carry the tag.

### Step 9 — Deployment notes (after all above merge)

Server: `git pull`; next cron run of `get_data.py --update` regenerates today's + yesterday's charts, indexes, and feeds with the new markup (per `update_charts`, `build_page.py:202-220`). Run the retrofit script once (Step 8). Optionally force an immediate refresh: `<venv python> top/build_page.py --lang en` (defaults to yesterday, rewrites `/index.html`). No nginx changes: `robots.txt`/`llms.txt` are served from the existing static root.

## Critical files & anchors

- `top/templates/base/chart.dust` — whole file; source of truth for Step 5 (per-lang copies are generated, never hand-edit them).
- `top/templates/chart.dust` — root fallback used by de/fr/ko/etc.; still carries the 2015-era twitter block and absolute http feed link; mirror Step 5 here with `{full_lang}` dust vars.
- `top/build_page.py` — `save_chart` (~line 150) and `update_feeds` (~line 229) for Step 4 context additions; `choose_template` (line 55) explains the two-flavor template system.
- `static/css/chart.css` — `.container` (line 146), `.row`/`.column`/`.rank`/`.cover-art` rules (lines 46–109), media query (line 60); shared by all archived pages, hence the `.chart` scoping rule.
- `top/l10nize.py` — `L10N_SRC_MAP` (line 11) lists exactly which base files regenerate; regeneration overwrites `<lang>_<name>` in place.

## Verification

Working dir: repo root. All python via the Docker command from "Architecture constraints".

1. **Fixture data** (pick yesterday's date, unpadded month/day):
   `mkdir -p static/en/wikipedia/2026/7 static/ar/wikipedia/2026/7 static/feeds && curl -so static/en/wikipedia/2026/7/10.json https://top.hatnote.com/en/wikipedia/2026/7/10.json && curl -so static/ar/wikipedia/2026/7/10.json https://top.hatnote.com/ar/wikipedia/2026/7/10.json`
   (These generated files + fixtures are scratch; `git status` must stay clean of them at the end — `.gitignore` already covers `static` data dirs; verify, otherwise clean up manually.)
2. **Build:** `<docker py2> python top/build_page.py --lang en --date 20260710` and `--lang ar --date 20260710`. Expect `successfully generated ...` lines, no tracebacks.
3. **Feed validity:** `xmllint --noout static/feeds/enwikipedia.rss` (well-formed); grep the file: channel `<title>English Wikipedia Top 100</title>` (non-empty lang — the live bug), `xml:lang="en"`, one `<atom:link rel="self"`, ≥1 `<media:thumbnail`, no `<copyright>`, guids start `https://`.
4. **New page, mobile:** `python3 -m http.server 8000 -d static` + browser tab at 390×844 on `http://localhost:8000/en/wikipedia/2026/7/10.html`:
   - `document.compatMode === 'CSS1Compat'` (standards mode)
   - `document.documentElement.scrollWidth <= 390` (no horizontal overflow)
   - `document.querySelectorAll('img[loading=lazy]').length === 100`
   - `document.querySelectorAll('svg.peity').length > 0` (sparklines render, no jQuery)
   - `JSON.parse(document.querySelector('script[type="application/ld+json"]').textContent).numberOfItems === 100`
   - `document.querySelector('link[rel=canonical]').href` starts `https://top.hatnote.com/en/wikipedia/`
   - press `j` twice / `k` once → viewport lands on row 2
   - `<html lang="en">`; for the ar page: `<html lang="ar" dir="rtl">` and layout mirrored
   - screenshot at 390px and 1280px — no clipped title, rank/cover/label columns intact
5. **Archived-page regression (the risky shared-CSS change):**
   `mkdir -p /tmp/top-old/en/wikipedia/2016/5 && curl -so /tmp/top-old/en/wikipedia/2016/5/1.html https://top.hatnote.com/en/wikipedia/2016/5/1.html`, copy current `static/css`, `static/js`, `static/fonts`, `static/img` into `/tmp/top-old/`, then `<docker py2> python top/retrofit_pages.py --root /tmp/top-old` (dry-run reports 1 modifiable) → `--apply` → re-run: reports 0. Serve `/tmp/top-old` and check at 390px AND 1280px: rows keep table layout, no horizontal scroll at 390px, sparklines still render via jQuery, no console errors beyond analytics. If the 2016 markup breaks under any new global CSS rule, move that rule under `.chart` scope.
6. **Regen diff审查:** `git diff --stat top/templates/` — only the 11 langs' generated files + base + root templates change; spot-read `ar_chart.dust` head (`dir="rtl"` on html, absent on body).

## Assumptions & contingencies

- **GA4 measurement ID `G-9LD7M2WME2`**: observed loading on the live site via Google's UA→GA4 shim for `UA-40320359-1`; `~/hatnote/listen-to-wikipedia` contains only the same dead UA snippet, no other ID found. If the GA admin console shows a different property, replace the ID everywhere: `grep -rl 'G-9LD7M2WME2' top/templates/` (base + root + regenerated files; fix base/root, regen).
- **`python:2.7` Docker image pip may fail** (ancient TLS/pip): retry with `pip install --index-url https://pypi.org/simple ...`; if still broken, run builds/l10nize on the server's existing py2 venv (`/home/hatnote/virtualenvs/top/bin/python`) instead — the repo edits are identical.
- **RSS guid http→https** re-surfaces up to 10 items per feed once in readers. Accepted; no mitigation.
- **`{lang}` var in root fallback chart head**: `data['lang']` is set in `save_chart` (line 176) so `<html lang="{lang}">` is safe there; index-family templates deliberately get no lang attribute.
- **Archived pages predating 2016** may use different markup than the 2016 fixture; the pre-decided fallback for any breakage is scoping the offending CSS rule under `.chart` (new pages only) — never reverting the viewport retrofit.
- **`no` (bokmål) strings** and other non-en yamls might lack `alt_tagline`/`rss_title`; fallback rule in Step 6.3 (reuse `index_title` / tag-stripped `tagline`) applies mechanically, no translation work required.
