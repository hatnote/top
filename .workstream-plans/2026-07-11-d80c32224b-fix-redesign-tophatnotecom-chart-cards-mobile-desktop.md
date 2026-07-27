---
id: 2026-07-11-d80c32224b
title: Fix + redesign top.hatnote.com chart cards (mobile & desktop)
status: implemented
workstream: top
repo: top
created: 2026-07-12
updated: 2026-07-12
tabled_note: ''
---

# Fix + redesign top.hatnote.com chart cards (mobile & desktop)

## Context

The just-deployed responsive design looks bad on phones: the black rank column wastes the left edge (mobile AND desktop), images stretch enormously tall, short titles wrap and look cut off, and the user reports pinch-zoom "not working". Root cause found and verified: the `@media (max-width: 640px)` block sits at chart.css line ~70 but the base rules for `.rank`/`.cover-art`/`.title` come LATER in the file with equal specificity, so **the entire mobile media query is dead code**. Beyond the fix, redesign the card: rank becomes a corner badge over the image (reclaims the left column everywhere), mobile gets a fixed 92×92 top-aligned thumbnail, titles get breathing room. One file changes: `static/css/chart.css`. No templates, no page regeneration, no retrofit, no cron changes.

## Diagnosis (verified this session, live site @ 390px viewport)

- Computed styles measured via headless Chrome: `.rank` 61.5px wide / 28.8px font; `.cover-art` 150px wide × **632px tall** (stretches to row height); `.label` squeezed to **109.7px**; `.title` 28.8px font with line-height 28.8px (wrapped lines overlap → "cut off" look). All the 640px media-query values (rank 2em, cover 96px, title 1.4em) are overridden because the media block precedes the base rules it must beat — same specificity, later-in-file wins.
- **Pinch zoom**: viewport meta is `width=device-width, initial-scale=1` on all pages (incl. retrofitted archives) — zoom is permitted. CDP `Input.synthesizePinchGesture` on the live homepage: visualViewport.scale went 1 → 2.0, no horizontal overflow. Nothing in CSS/JS blocks zoom (no `touch-action`, no `user-scalable` restriction, `top.js` has no touch handlers). What is impossible on ANY responsive page is zooming OUT below 100% — pre-deploy pages rendered at ~980px so both directions worked. No code change; report this to the user and include a real-device check post-deploy.
- **Page generations sharing chart.css** (must not break):
  - New (2026-07 deploy): `<ol class="chart">` → flex rules under `.chart` apply; cover art is `<a class="column cover-art"><img></a>` with absolutely-positioned img.
  - Old (2016–2023 archives, ~105k pages): plain `<ul>` (NO `chart` class) → `.chart` rules never applied; they use the `display: table` base rules; cover art is an empty `<a class="column cover-art cover-N">` with per-page inline `<style>` `background: url(...); background-size: cover`.
  - Row markup classes (`.row`, `.column.rank > p > a`, `.cover-art`, `.label`, `.title`, `.summary`, `.meta-area`) are IDENTICAL across generations. `.row`/`.title` appear in chart templates only (verified by grep of all template families).
  - RTL: new ar/fa/ur pages have `<html dir="rtl">`; OLD ar pages have NO dir attribute and inject inline `.rank { border-radius: 0 7px 7px 0 }` overrides (border-radius only — harmless to the new badge).
- Local new-format fixtures exist: `static/en/wikipedia/2026/7/10.html`, `static/ar/wikipedia/2026/7/10.html`, `static/index.html` (all reference `css/chart.css` relatively). No old-format pages locally — download from live site (step 2).
- gotcha: live-site curls MUST use `--compressed` (nginx gzips; a plain `curl | grep` silently matches nothing — this burned a check during the last deploy).

## Card design (target)

- **Rank badge**: the `.rank` element stops being a full-height column and becomes a small dark chip pinned to the card's top-left corner, overlaying the image: `rgba(13,15,5,0.82)` background, white text, Roboto Slab, `border-radius: 7px 0 7px 0` (outer corner matches the card's 7px radius). RTL pages pin it top-right. Applies to ALL page generations (base rule) — reclaims ~61px of text width on desktop, ~45px on mobile, on 105k archive pages too.
- **Desktop (>640px)**: cover image stays 150px wide, full row height (not a complaint; magazine look retained). Title stays 2em but line-height 1em → 1.2 (fixes overlapping wrapped lines).
- **Mobile (≤640px)**: every row becomes flex (this also converts old table-layout archive rows — `display: table-cell` children blockify inside a flex container, so old bg-image cover divs accept explicit dimensions); cover art becomes a fixed **92×92 top-aligned square** (object-fit / background-size cover crop), so row height is driven by text, never the image; title 1.3em; tightened margins.

## Approach

### 1. Edit `static/css/chart.css` (the only code change)

Line numbers are hints from this session's read; anchor on the quoted selector text.

**1a. `.row` base rule (line 46)** — add `position: relative;` (containing block for the badge) to the existing declaration block `​.row { display: table; margin-bottom: 0.5em; ... }`.

**1b. DELETE both media-query blocks where they currently sit** (lines ~60–68 `@media (max-width: 800px)` and ~70–79 `@media (max-width: 640px)`). They are re-added at the file end in 1f.

**1c. `.chart .rank` flex-column rule (line 98)** — delete the whole line `.chart .rank { display: flex; flex: none; align-items: center; justify-content: center; box-sizing: content-box; }` (rank is no longer a flex column).

**1d. Replace the `.rank` block (lines ~104–116)** — currently `font-size: 2em; width: 50px; ... border-radius: 7px 0 0 7px;` — with exactly:

```css
.rank {
  font-family: "Roboto Slab", serif;
  font-size: 1.15em;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  background: rgba(13, 15, 5, 0.82);
  color: #fbfbfb;
  padding: 0.1em 0.55em;
  border-radius: 7px 0 7px 0;
}

.rank p {
  margin: 0;
}

[dir="rtl"] .rank {
  left: auto;
  right: 0;
  border-radius: 0 7px 0 7px;
}
```

Keep the existing `.rank a { color: #fbfbfb; ... }` block untouched. `.rank p { margin: 0 }` is REQUIRED — the `<p>` inside `.rank` otherwise carries default 1em margins that ruin the chip. Old ar pages' inline `.rank { border-radius: 0 7px 7px 0 }` (they lack `dir="rtl"`) loads after chart.css and only changes the radius — acceptable.

**1e. Archive polish + title fix:**
- After the `.cover-art { background-size: cover; width: 150px; }` block (line ~123), add: `ul .row .cover-art { border-radius: 7px 0 0 7px; }` — old pages' rows don't have `overflow: hidden`, and with the rank cell gone the bg-image div is now the leftmost visible corner; this rounds it to match the card. (`ul` scoping excludes new `<ol class="chart">` pages, whose row-level `overflow: hidden` already clips.)
- `.title` block (line ~139): change `line-height: 1em;` → `line-height: 1.2;`. Leave font-size/margins as-is (desktop).

**1f. Append at the very END of the file** (after `.projects { margin: 2em 4em; }`):

```css
@media (max-width: 800px) {
  .ultra {
    display: block;
  }

  .container {
    padding: 0 1em;
  }
}

@media (max-width: 640px) {
  h1 { font-size: 2.25em; }
  .subtitle { font-size: 1.15em; }
  .row { display: flex; }
  .label { flex: 1; min-width: 0; }
  .rank { font-size: 1em; }
  .cover-art {
    flex: none;
    width: 92px;
    height: 92px;
    align-self: flex-start;
    border-radius: 0 0 7px 0;
    overflow: hidden;
  }
  [dir="rtl"] .cover-art { border-radius: 0 0 0 7px; }
  .title { font-size: 1.3em; margin: 0.5em 0.5em 0.25em 0.6em; }
  .summary { font-size: 0.95em; margin: 0 0.75em 0.75em 0.75em; }
  .meta-area { margin: 0 0 0.75em 0.75em; }
  .streak { padding-left: 0.5em; }
  .ext-icon { margin: 0.35em; }
}
```

Why this works now: every selector in the 640px block is single-class (0,0,1,0), same specificity as the base rules but LATER in the file → wins. The only 2-class base rules (`.chart .cover-art { flex: none; position: relative; }`, `.chart .label`, `.chart .row`) set properties the media query doesn't fight (position/flex direction), so no specificity collision. `.row { display: flex }` in the query converts OLD table rows to flex on mobile; their `.cover-art` (table-cell → blockified flex item) then honors the 92×92 box and `background-size: cover` crops correctly. New pages' `<img>` (absolute, 100%/100%, object-fit cover) fills the same box.

### 2. Local verification before deploy (gate for step 3)

Download old-format fixtures into the local gitignored static tree so relative `../../../../css/chart.css` resolves to the EDITED file (`--compressed` mandatory):

```bash
mkdir -p static/en/wikipedia/2016/5 static/ar/wikipedia/2021/1
curl -s --compressed -o static/en/wikipedia/2016/5/1.html https://top.hatnote.com/en/wikipedia/2016/5/1.html
curl -s --compressed -o static/ar/wikipedia/2021/1/1.html https://top.hatnote.com/ar/wikipedia/2021/1/1.html
```

Serve `static/` (`python3 -m http.server 8901`, cwd `static/`) and assert with the browser tool. For each page × viewport, measure via `page.evaluate` on the FIRST `li.row`:

| page | viewport | assertions |
|---|---|---|
| `/en/wikipedia/2026/7/10.html` (new en) | 390×844 | cover rect = 92×92; label rect width ≥ 230; title fontSize ≈ 18.7px, lineHeight ≥ 22px; row height < 450; rank rect top ≈ row top AND left ≈ row left (badge overlay); `document.documentElement.scrollWidth == 390` (no h-overflow) |
| same | 1280×900 | cover-art rect left ≈ row left (no rank gutter); cover width 150; rank overlays cover top-left; title lineHeight ≈ 38.4px (1.2×2em) |
| `/ar/wikipedia/2026/7/10.html` (new RTL) | 390×844 | rank rect right ≈ row right (RTL badge); cover art on the RIGHT edge of row |
| `/en/wikipedia/2016/5/1.html` (old table markup) | 390×844 | row `display: flex` computed; cover rect = 92×92; label text not overlapped (title lineHeight ≥ 22px); rank badge overlays image |
| same | 1280×900 | old table layout intact: cover rect ≈ 150 wide full row height; badge top-left; summary/meta text present and not clipped |
| `/ar/wikipedia/2021/1/1.html` (old ar, NO dir attr) | 390×844 | badge lands top-LEFT (page is LTR-structured); no text/badge overlap; cover 92×92 |
| `/index.html` (homepage) | 390×844 | same as new en mobile |

Also take screenshots at 390px (new en, old en) and eyeball: badge legible on image, no giant vertical images, titles readable. Any failed assertion → fix CSS locally, re-run; do NOT proceed to deploy.

### 3. Deploy to wenli

CSS-only deploy; reuse the proven protocol from the previous deployment (temp passwordless sudo keeps `/home/hatnote/top` ownership clean — a pull as mahmoud would leave mahmoud-owned `.git` objects that can break future hatnote pulls).

1. **USER ACTION — tell the user to run on wenli** (agent says when):
   ```bash
   echo 'mahmoud ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/99-deploy-tmp && sudo chmod 440 /etc/sudoers.d/99-deploy-tmp && sudo visudo -c
   ```
   Verify: `ssh wenli 'sudo -n true && echo SUDO_OK'` → `SUDO_OK`.
2. Commit + push (chart.css is already git-tracked since the last deploy; fixtures downloaded in step 2 live in gitignored paths and MUST NOT be staged — stage the one file explicitly):
   ```bash
   git add static/css/chart.css
   git status --short   # exactly 1 staged path
   git commit -m "chart cards: rank badge overlay, fixed mobile thumbnails, live media queries (were dead code below base rules)"
   git push origin master
   ```
3. Pull on wenli:
   ```bash
   ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top && git pull origin master'"
   ```
   Expect fast-forward touching only `static/css/chart.css`. Running pollers/cron are unaffected (CSS is not read by get_data.py); no regeneration or retrofit needed since HTML is unchanged.
4. **USER ACTION — revoke**: user runs `sudo rm /etc/sudoers.d/99-deploy-tmp` on wenli; agent verifies `ssh wenli 'sudo -n true 2>&1'` FAILS with "a password is required".

### 4. Post-deploy verification (live)

```bash
curl -s --compressed https://top.hatnote.com/css/chart.css | grep -c 'position: absolute'   # ≥ 2 (badge + existing img rule)
curl -s --compressed https://top.hatnote.com/css/chart.css | tail -30                        # ends with the 640px media block
```

Browser tool against the LIVE site (`https://top.hatnote.com/`, `/en/wikipedia/2016/5/1.html`, `/ar/wikipedia/2026/7/10.html`) at 390×844: re-run the same computed-style assertions as step 2 (nginx `expires 1h` is client-side; a fresh headless load gets the new CSS immediately). Then report to the user, including: pinch-zoom-IN verified working (emulated); zoom-out below 100% is impossible on responsive pages by design; ask them to re-test pinch on their device against the fixed layout and report the exact device/browser if it still fails.

## Critical files & anchors

- `static/css/chart.css` — the whole change. Anchors: `.row {` (l.46), dead `@media` blocks (l.60/70), `.chart .rank` (l.98), `.rank {` (l.104), `.cover-art {` (l.123), `.title {` (l.139), file end after `.projects`.
- `top/templates/chart.dust:53-66` — canonical row markup the CSS must serve (do not edit).
- Live old-page markup references: `https://top.hatnote.com/en/wikipedia/2016/5/1.html` (table-era, bg-image covers), `/ar/wikipedia/2021/1/1.html` (old ar, no dir attr, inline `.rank` radius overrides).

## Verification

Acceptance: (a) all step-2 local assertions pass for all 7 page×viewport combos; (b) commit touches exactly `static/css/chart.css`; (c) wenli pull fast-forwards that one file; (d) live chart.css tail shows the media block and live 390px assertions pass; (e) sudo revoked and verified failed; (f) user-visible: no left gutter on desktop or mobile, 92×92 thumbnails on mobile, titles wrap with normal leading, archives unbroken.

## Assumptions & contingencies

- **Badge overlay applies to all page generations** (base-rule change) — chosen because the user called out wasted left space generically and archives share the CSS. If archive spot-checks in step 2 reveal breakage in some untested era (e.g., 2018–2020 variants), fallback: scope the badge rules under `.chart` (new pages only) and restore the previous `.rank` column rules inside a `ul .row .rank` selector for old pages — decision pre-made, no redesign needed.
- **Desktop keeps the 150px full-height image** (only the rank column was the desktop complaint). If the user wants square thumbs on desktop too, it is the same `.cover-art` box treatment moved out of the media query — not done now.
- **92×92 mobile thumbnail** (standard news-card size; 4.2:1 text-to-image width on a 390px phone). Any value 88–100px works; changing it is a one-line edit in the media block.
- **Pinch zoom needs no code change** (verified permitted + functional in emulation). If the user's device still can't zoom after the layout fix, collect device/browser/URL — likely browser-specific; nothing in the page restricts it.
- **Tonight's 21:00 cron** regenerates pages with unchanged templates — no interaction with this CSS deploy in either order.
