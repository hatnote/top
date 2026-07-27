---
id: 2026-07-12-c2e1b4df86
title: Polish mobile card spacing + move sparkline below view count (top.hatnote.com)
status: implemented
workstream: top
repo: top
created: 2026-07-12
updated: 2026-07-12
tabled_note: ''
---

# Polish mobile card spacing + move sparkline below view count (top.hatnote.com)

## Context

The mobile card redesign (float-wrapped 92×92 image, badge rank, full-width meta bottom) is deployed and working, but the user finds it unpolished: text spacing too tight, text too close to the card border, and the sparkline should sit below the view count instead of inline beside it. Fix by replacing the `@media (max-width: 640px)` block in `static/css/chart.css` with Tailwind-scale spacing values (px). One file changes; desktop (>640px) stays untouched.

## Current state (measured live @ 390px, base font 14.4px — all verified this session)

- Title: 18.72px / line-height 22.46 (1.2), margin `7.5px 9.4px 3.7px` — cramped top corner.
- Summary: 13.68px / line-height 16.4 (**1.2 — the "too tight" complaint**), side margins 6.8px.
- Meta-area: 12.96px, side margins 6.5px. Insets are inconsistent (9.4 / 6.8 / 6.5px) and all too small — the "too close to border" complaint.
- Cover: 92×92, margin `0 10.8px 5.76px 0`.
- **Sparkline DOM (identical across page generations, both verified)**: an `svg.peity` (50×14) sits INSIDE `p.views`, inserted as a sibling right after the hidden `span.sparkline` data span. New pages: `static/js/top.js` `initSparklines()` creates it (`svg.setAttribute('class', 'peity')`). Old pages (2016–2023 archives): `jquery.peity.min.js` does `$el.hide().after($svg)` — same position. Base rule `.peity { margin-left: 1em }` (chart.css ~line 312) makes it render inline to the right of the views text. So `.views .peity { display: block; ... }` in the mobile media query moves it below the view count on ALL generations; specificity (0,0,2,0) beats base `.peity` (0,0,1,0).
- Meta markup order: `p.views` (text + meta span + hidden sparkline span + svg.peity), `p.streak`, then float-right icon anchors (`span.ext-icon` on new pages ×2, `img.twitter-icon` on old pages). With `.views` made `display: block`, the streak (inline-block) starts a new line and the right-floated icons share that line — verified via injected-CSS prototype.

## Target design (prototyped in-browser this session; all values confirmed rendering correctly)

Tailwind approximations: side inset 16px (p-4), block gaps 12px (mb-3/mt-3), image gutter 12px (gap-3), image 96×96 (w-24), title leading-snug 1.375, body leading-normal 1.5, 8px (pt-2) after the dotted meta divider.

Meta area stacks: views text line → sparkline block (left-aligned) below it → streak line with icons floated right. Verified metrics from the prototype: title lh 25.74px, summary lh 20.52px, peity `display: block` left-aligned at meta edge, streak below peity, icons right-aligned on the streak line, row height ~320px (up from 241 — acceptable, airier).

## Approach

### 1. Replace the entire `@media (max-width: 640px)` block in `static/css/chart.css` (the only code change)

The block currently sits at lines ~380–401 (file end, after the 800px media query). Line numbers are hints; anchor on `@media (max-width: 640px)`. Replace the whole block with exactly:

```css
@media (max-width: 640px) {
  h1 { font-size: 2.25em; }
  .subtitle { font-size: 1.15em; }
  .row, .chart .row { display: block; overflow: hidden; }
  .column, .chart .column { display: block; }
  .label { overflow: visible; }
  .chart .label { flex: initial; min-width: initial; }
  .rank { font-size: 1em; }
  .cover-art {
    float: left;
    width: 96px;
    height: 96px;
    margin: 0 12px 8px 0;
    overflow: hidden;
  }
  [dir="rtl"] .cover-art { float: right; margin: 0 0 8px 12px; }
  .title { font-size: 1.3em; line-height: 1.375; margin: 12px 16px 4px; }
  .summary { font-size: 0.95em; line-height: 1.5; margin: 0 16px 12px; }
  .meta-area { clear: both; margin: 0 16px 12px; }
  .views { display: block; margin: 8px 0 0; }
  .views .peity { display: block; margin: 6px 0 0; }
  .streak { padding: 0; margin: 6px 0 0; }
  .ext-icon { margin: 2px 0 0 12px; }
}
```

Deltas vs the deployed block (everything else is carried over verbatim — do NOT touch the structural rules `.row/.column/.label/.rank/[dir=rtl]`):
- `.cover-art`: 92→96px square, margin `0 0.75em 0.4em 0` → `0 12px 8px 0` (RTL mirrored).
- `.title`: adds `line-height: 1.375`; margin `0.4em 0.5em 0.2em 0.5em` → `12px 16px 4px`.
- `.summary`: adds `line-height: 1.5` (was inheriting 1.2 from base); margin `0 0.5em 0.4em 0.5em` → `0 16px 12px`.
- `.meta-area`: margin `0 0.5em 0.5em 0.5em` → `0 16px 12px`.
- NEW `.views { display: block; margin: 8px 0 0; }` — full-width line, pushes streak to next line (base rule has it `inline-block; margin: 0.5em 0`).
- NEW `.views .peity { display: block; margin: 6px 0 0; }` — sparkline on its own line under the view count, left-aligned; kills base `margin-left: 1em`. In RTL a fixed-width block start-aligns right — correct.
- `.streak`: `padding-left: 0.5em` → `padding: 0; margin: 6px 0 0;` (base padding-left 1em must be zeroed; it no longer separates from views since it's on its own line).
- `.ext-icon`: `margin: 0.35em` → `2px 0 0 12px`.

No template, JS, or page regeneration. Old pages' `img.twitter-icon` (base: `float: right; margin: 1em`) is intentionally untouched — it already renders bottom-right acceptably.

### 2. Local verification (gate for deploy)

Fixtures already exist in the gitignored static tree: `static/en/wikipedia/2026/7/10.html`, `static/ar/wikipedia/2026/7/10.html`, `static/index.html`, `static/en/wikipedia/2016/5/1.html` (old table markup), `static/ar/wikipedia/2021/1/1.html` (old ar, no dir attr). If missing, re-download with `curl -s --compressed -o <path> https://top.hatnote.com/<path-under-static>` (`--compressed` is mandatory — nginx gzips and plain curl silently yields garbage).

Serve: `cd static && python3 -m http.server 8901 --bind 0.0.0.0` (a prior serve attempt without `--bind` returned ERR_EMPTY_RESPONSE; this form is verified working).

Browser-tool assertions on the FIRST/second `li.row`, cache disabled (`page.setCacheEnabled(false)`) + cache-bust query param:

| page | viewport | assert (computed styles / rects) |
|---|---|---|
| `/en/wikipedia/2026/7/10.html` | 390×844 | cover 96×96; title lineHeight ≈ 25.74px, marginTop 12px, side margins 16px; summary lineHeight ≈ 20.52px; `svg.peity` display `block`, its rect.top ≥ views-text top + 15, rect.left ≈ meta-area content left (±2px); streak rect.top ≥ peity rect.bottom; ext-icon right edge ≈ meta-area right (±4px) and vertically on the streak line (±12px); `document.documentElement.scrollWidth == 390` |
| same | 1280×900 | UNCHANGED desktop: cover 150px wide; `svg.peity` display `inline`; title margin `7.2px 0 7.2px 7.2px` (base 0.5em) and lineHeight 34.56px |
| `/en/wikipedia/2016/5/1.html` | 390×844 | row display block; cover 96×96; peity display block below views text; twitter-icon still right-aligned; no h-overflow |
| `/ar/wikipedia/2026/7/10.html` | 390×844 | cover floats right (rect.right ≈ row right); peity block start-aligned at the RIGHT edge of meta-area (RTL); rank badge top-right |
| `/index.html` | 390×844 | same as new-en mobile spot checks (cover 96, peity block) |

Screenshot 390px new-en and old-en; eyeball: breathing room at all four card edges, sparkline under the view count, streak+icons on one bottom line, no clipped/overlapping text. Any failure → fix CSS locally and re-run; do NOT deploy.

### 3. Deploy to wenli

`static/` is gitignored but `chart.css` is force-tracked — staging REQUIRES `-f`:

```bash
cd ~/hatnote/top
git add -f static/css/chart.css
git status --short   # exactly 1 staged path (untracked .env / .workstream-plans are expected noise)
git commit -m "mobile cards: tailwind-scale spacing, sparkline below view count"
git push origin master
```

Check sudo: `ssh wenli 'sudo -n true && echo SUDO_OK'`. If it fails (the temp sudoers file `/etc/sudoers.d/99-deploy-tmp` was to be revoked after the last deploy), tell the user to run on wenli:
`echo 'mahmoud ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/99-deploy-tmp && sudo chmod 440 /etc/sudoers.d/99-deploy-tmp && sudo visudo -c`
then re-verify.

Pull: `ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top && git pull origin master'"` — expect fast-forward touching only `static/css/chart.css`.

After live verification (step 4), tell the user to revoke: `sudo rm /etc/sudoers.d/99-deploy-tmp` on wenli; verify `ssh wenli 'sudo -n true 2>&1'` fails with "a password is required".

### 4. Post-deploy verification (live)

- `curl -s --compressed https://top.hatnote.com/css/chart.css | tail -25` — must show the new block incl. `.views .peity { display: block; ... }`.
- Browser tool on `https://top.hatnote.com/` and `/en/wikipedia/2016/5/1.html` at 390×844 (fresh cache + cache-bust param — nginx sends `max-age=3600`, a stale cached copy gave false failures during the previous deploy): re-run the step-2 mobile assertions.
- Report before/after to the user with a live screenshot.

## Critical files & anchors

- `static/css/chart.css` — `@media (max-width: 640px)` block at file end (~380–401): the whole change.
- `static/js/top.js` `initSparklines()` (~line 6–41) — proves `svg.peity` lands inside `p.views` on new pages (do not edit).
- `static/js/jquery.peity.min.js` `prepare()` (`$el.hide().after(this.$svg=...)`) — proves same DOM position on old pages (do not edit).
- `top/templates/chart.dust:62-69` — meta-area markup order (views → streak → icon anchors) the stacking relies on (do not edit).

## Verification

Acceptance: (a) all step-2 mobile assertions pass on all 5 pages; (b) desktop 1280px checks confirm zero change above 640px; (c) commit touches exactly `static/css/chart.css` and wenli pull fast-forwards it; (d) live 390px assertions pass and the live screenshot shows: ≥16px side insets, summary leading 1.5, sparkline directly under the view count, streak+icons on the bottom line; (e) sudo revoked and verified failed.

## Assumptions & contingencies

- **Sparkline-below-views is mobile-only** (desktop keeps the long-standing inline-right placement). If the user wants it stacked on desktop too, move the `.views .peity` rule out of the media query and drop the base `.peity { margin-left: 1em }`.
- **Cover bumped 92→96px** (Tailwind w-24). If the wrap column feels too narrow on small phones, revert width/height to 92px — no other rule depends on the value.
- **Image stays flush to the card corner** (badge overlays it); only text got insets. If the user wants the image inset too, add `margin: 12px 0 8px 12px` ([dir=rtl] mirrored) and `border-radius: 7px` to `.cover-art` — not done now.
- **Old-page `img.twitter-icon` margins untouched** (renders acceptably; 105k archive pages, don't gold-plate). If it looks misaligned in step-2 old-page screenshots, add `.twitter-icon { margin: 2px 0 0 12px; }` beside the `.ext-icon` rule.
- Streak `<p>` is empty on no-streak articles (verified in 2016 fixture) — as inline-block with 6px top margin it contributes ~6px dead space on those cards; accepted (pre-existing).
