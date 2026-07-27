---
id: 2026-07-11-1e73886357
title: Deploy top.hatnote.com changes to wenli (agent-driven)
status: implemented
workstream: top
repo: top
created: 2026-07-11
updated: 2026-07-11
tabled_note: ''
---

# Deploy top.hatnote.com changes to wenli (agent-driven)

## Context

The mobile/machine-readability implementation (py3 port, responsive templates, JSON-LD/OG, RSS fixes, robots/llms.txt, retrofit script) is complete and verified locally but uncommitted on `master` in `~/hatnote/top`. Deploy flow: commit + push to `github.com/hatnote/top`, pull onto host `wenli`, create a python3.10 venv, sanity-run historical dates, repoint cron, regenerate the whole site's latest charts in the new format, retrofit ~70k archived pages. **The agent drives every server step non-interactively over `ssh wenli` using temporary passwordless sudo that the user grants at step 0 and revokes at the final step — the agent must explicitly tell the user when to grant and when to revoke.** Nothing is left for the nightly cron to clean up: feeds, homepages, and any in-flight fetch day are restored by the plan itself.

## Server facts (verified this session)

- **wenli**: Ubuntu 18.04.6, tailnet `100.64.209.11`. `ssh wenli` works as user `mahmoud` (uid 1000; groups `sudo`, `hatnote`). No direct hatnote SSH. sudo is password-gated until step 0.
- **Clock caution**: wenli's `date -u` read ~4h ahead of the laptop's clock during research. Never compute deploy timing from the laptop clock — use wenli's own `date`/`ps` output and the repo's `check_most_recent()` for date math.
- **Repo**: `/home/hatnote/top`, owned `hatnote:hatnote`, group-writable. `origin = git@github.com:hatnote/top.git`, `master` @ `befe5f3`, clean, identical to local `origin/master`. Server-local untracked files (`access.log`, `backfill.sh`, `logs/cron_out/`, `static_bak/`) — leave untouched.
- **Pythons**: `/usr/bin/python3` = 3.6.9 (too old); `/usr/bin/python3.10` present, `venv`+`ensurepip` verified (pip 22.3.1). Old venv `/home/hatnote/virtualenvs/top` = Python 2.7.17 — keep untouched as rollback. `/home/hatnote/virtualenvs/` is `hatnote:hatnote` group-writable.
- **nginx**: `root /home/hatnote/top/static/`, `expires 1h` (client-side only). `robots.txt`/`llms.txt`/`js/top.js` serve automatically once present — no nginx change.
- **Cron** (hatnote's user crontab, contents supplied by user): one env line `TOP_PYTHON_BIN=/home/hatnote/virtualenvs/top/bin/python` + 27 per-lang entries at 21:00–21:07 server time, each `get_data.py --update --lang <L> --project wikipedia --poll 36h --poll-interval 15m 2>&1 | tee -a logs/cron_out/<L>.txt`. Langs: `ko en de fr et sv da it ca es zh ur kn no bn id ta lv el fa cs te pa fi or ar gl hu`. The string `virtualenvs/top/bin/python` appears exactly once (the env line) — a `sed` on it is safe. Pre-existing quirk: `bn` tees to `gn.txt`; leave.
- **Poller lifecycle**: each cron entry polls every 15 min until Wikimedia publishes that day's data (~02:45 server time next day), then renders and exits. At research time 29 `get_data.py` processes were alive: the current 21:0x batch plus stale ones started in 2025 (kill-safe).
- **Port compatibility**: ported `top/get_data.py` argparser (lines 473–486) supports exactly the cron flags (`--update --lang --project --poll --poll-interval`); `check_most_recent(lang, project)` in `top/build_page.py` returns the newest date with data on disk.
- **All 27 cron langs exist in `LOCAL_LANG_MAP`** (`top/common.py`) — langs without per-lang templates fall back to root `chart.dust` by design.

## Approach

Command convention for all server steps: `ssh wenli "sudo -n -H -u hatnote bash -lc '<cmd>'"` (`-n` fails loudly if sudo isn't passwordless yet; `-H` forces hatnote's HOME so git uses hatnote's SSH key and files stay `hatnote:hatnote`). Root-level commands (crontab) drop the `-u hatnote`.

### 0. USER ACTION — grant temporary passwordless sudo

Tell the user to run this on wenli (file name must contain no dots — sudoers ignores dotted files):

```bash
echo 'mahmoud ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/99-deploy-tmp && sudo chmod 440 /etc/sudoers.d/99-deploy-tmp && sudo visudo -c
```

Agent waits, then verifies: `ssh wenli 'sudo -n true && echo SUDO_OK'` → `SUDO_OK`. Do not proceed without it.

### 1. Local: commit and push (laptop, `~/hatnote/top`)

Stage explicitly — NEVER `git add -A` (must exclude `.env`, `.workstream-plans/`, `.venv/`):

```bash
git add requirements.txt top/ static/css/chart.css
git add -f static/js/top.js static/robots.txt static/llms.txt   # static/ is gitignored; -f required or they never reach the server
```

Check `git status --short`: ~104 staged paths (all of `top/` incl. new `top/retrofit_pages.py`, templates, chart.css, the 3 forced static files); nothing from `.env`/`.venv`/`static/en/...`. `__pycache__` contents are covered by the `*.pyc` gitignore rule.

```bash
git commit -m "mobile + machine readability: py3 port, responsive templates, JSON-LD/OG, RSS fixes, robots/llms.txt, archive retrofit script"
git push origin master
```

### 2. Server: snapshot state, kill pollers

```bash
ssh wenli 'date; ps aux | grep get_data.py | grep -v grep' | tee /tmp/wenli-pollers-before.txt
```

Decide catchup need from the snapshot (rule, using wenli's clock): pollers with a `21:0x` START from the current cron batch exist whenever server time is between 21:00 and ~02:45. Record `IN_FLIGHT`:
- server hour ≥ 21 → `IN_FLIGHT` = server `date +%Y%m%d`
- server hour < 03 → `IN_FLIGHT` = server `date -d yesterday +%Y%m%d`
- otherwise (quiet window) → no live batch, `IN_FLIGHT` empty; only stale pollers may exist.

Then kill everything (stale 2025 pollers are kill-safe; a live batch must NOT survive the pull — a py2 poller succeeding after the pull would render the new templates with the old context and produce broken heads):

```bash
ssh wenli 'sudo -n -u hatnote pkill -f get_data.py; sleep 2; ps aux | grep get_data.py | grep -v grep | wc -l'   # → 0
```

### 3. Pull + create top3 venv

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top && git rev-parse HEAD'"   # record rollback hash (expect befe5f3...)
ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top && git pull origin master'"
```

If the pull fails on SSH auth (hatnote's GitHub key unverified): `git pull https://github.com/hatnote/top.git master` — public repo, no auth.

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc '/usr/bin/python3.10 -m venv /home/hatnote/virtualenvs/top3 && /home/hatnote/virtualenvs/top3/bin/pip install -r /home/hatnote/top/requirements.txt'"
ssh wenli "sudo -n -H -u hatnote bash -lc '/home/hatnote/virtualenvs/top3/bin/python -c \"import ashes, yaml, boltons, lithoxyl, babel, dateutil; print(\\\"imports ok\\\")\"'"
```

If pip cannot reach PyPI or a dep fails: stop and report — cron still points at the untouched py2 venv, site unaffected.

### 4. Sanity run on historical date (regenerates real live pages — accepted)

Before touching cron. Two days ago by wenli's clock (data guaranteed published, no polling):

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top && D=\$(date -u -d \"2 days ago\" +%Y%m%d) && DP=\$(date -u -d \"2 days ago\" +%Y/%-m/%-d) && echo \$DP > /tmp/deploy-dp.txt &&
  /home/hatnote/virtualenvs/top3/bin/python top/get_data.py --update --lang en --project wikipedia --date \$D &&
  /home/hatnote/virtualenvs/top3/bin/python top/get_data.py --update --lang ar --project wikipedia --date \$D'"
```

Expected: `successfully generated ...` lines (dated html, month/year/project indexes, `static/feeds/{en,ar}wikipedia.rss`), exit 0, no traceback (DeprecationWarnings re `utcnow`/`codecs.open` are known-cosmetic). This date is older than the newest chart so `index.html` is NOT touched. Verify artifacts (`DP` = the `Y/M/D` path fragment from above):

```bash
ssh wenli "bash -lc 'cd /home/hatnote/top && DP=\$(cat /tmp/deploy-dp.txt) &&
  grep -c \"name=\\\"viewport\\\"\" static/en/wikipedia/\$DP.html &&        # 1
  grep -c \"loading=\\\"lazy\\\"\" static/en/wikipedia/\$DP.html &&          # 100
  grep -c \"application/ld+json\" static/en/wikipedia/\$DP.html &&           # 1
  grep \"rel=\\\"canonical\\\"\" static/en/wikipedia/\$DP.html &&            # https://top.hatnote.com/en/wikipedia/...
  grep -c \"dir=\\\"rtl\\\"\" static/ar/wikipedia/\$DP.html &&               # 1
  xmllint --noout static/feeds/enwikipedia.rss && echo FEED_OK &&
  grep \"<title>English Wikipedia Top 100</title>\" static/feeds/enwikipedia.rss &&
  grep -c \"https://top.hatnote.com\" static/en/wikipedia/\$DP.json'"        # >0 (permalinks now https)
```

Any failed check → stop, do NOT repoint cron; go to Rollback. (Reads need no sudo — mahmoud is in group `hatnote`.)

### 5. Repoint cron (non-interactive, with backup)

```bash
ssh wenli 'sudo -n crontab -u hatnote -l > /home/mahmoud/hatnote-cron-backup.txt &&
  sed "s|virtualenvs/top/bin/python|virtualenvs/top3/bin/python|" /home/mahmoud/hatnote-cron-backup.txt > /tmp/hatnote-cron-new.txt &&
  diff /home/mahmoud/hatnote-cron-backup.txt /tmp/hatnote-cron-new.txt; sudo -n crontab -u hatnote /tmp/hatnote-cron-new.txt &&
  sudo -n crontab -u hatnote -l | grep TOP_PYTHON_BIN'
```

The `diff` must show exactly one changed line (the `TOP_PYTHON_BIN` env line — the path string occurs nowhere else, verified). Final grep → `.../virtualenvs/top3/bin/python`. Backup stays at `/home/mahmoud/hatnote-cron-backup.txt` for rollback.

### 6. Full regeneration + in-flight catchup (the cleanup — nothing left for cron)

**6a. Regenerate the newest chart for ALL 27 langs in the new format** (also rewrites every lang index + the site homepage, restores the en/ar feed windows shifted by step 4, and exercises every template path now instead of unattended at 21:00). `LATEST` comes from the repo's own `check_most_recent()`:

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top &&
  LATEST=\$(/home/hatnote/virtualenvs/top3/bin/python -c \"import sys; sys.path.insert(0, \\\"top\\\"); from build_page import check_most_recent; print(check_most_recent(\\\"en\\\", \\\"wikipedia\\\").strftime(\\\"%Y%m%d\\\"))\") &&
  echo LATEST=\$LATEST &&
  nohup bash -c \"for L in ko en de fr et sv da it ca es zh ur kn no bn id ta lv el fa cs te pa fi or ar gl hu; do
    /home/hatnote/virtualenvs/top3/bin/python top/get_data.py --update --lang \\\$L --project wikipedia --date \$LATEST || echo FAIL_\\\$L
  done; echo REGEN_DONE\" > logs/deploy_regen.log 2>&1 &'"
```

Poll until done (expect 10–30 min; each lang refetches traffic/images/summaries from live APIs):

```bash
ssh wenli 'grep -c REGEN_DONE /home/hatnote/top/logs/deploy_regen.log; grep -c "successfully generated" /home/hatnote/top/logs/deploy_regen.log; grep -i "FAIL_\|Traceback" /home/hatnote/top/logs/deploy_regen.log | sort | uniq -c'
```

Acceptance: `REGEN_DONE` present, zero `FAIL_*`/`Traceback` lines. A single-lang failure → inspect that lang's output in the log; if the cause is lang-specific data (e.g., an API hiccup) re-run just that lang; if the cause is systemic (template/context error) → Rollback. Then confirm the homepage flipped to the new pipeline:

```bash
ssh wenli 'grep -c "application/ld+json" /home/hatnote/top/static/index.html'   # → 1
```

**6b. In-flight catchup — only if step 2 recorded a non-empty `IN_FLIGHT`** (a live 21:0x batch was killed mid-fetch). Re-launch the equivalent work under the new venv; each lang exits as soon as Wikimedia publishes, identical to what cron would have done:

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc 'cd /home/hatnote/top &&
  nohup bash -c \"for L in ko en de fr et sv da it ca es zh ur kn no bn id ta lv el fa cs te pa fi or ar gl hu; do
    /home/hatnote/virtualenvs/top3/bin/python top/get_data.py --update --lang \\\$L --project wikipedia --date <IN_FLIGHT> --poll 12h --poll-interval 15m 2>&1 | tee -a logs/cron_out/\\\$L.txt
  done; echo CATCHUP_DONE >> logs/deploy_regen.log\" > /dev/null 2>&1 &'"
ssh wenli 'ps aux | grep get_data.py | grep -v grep | head -3'   # exactly one poller (sequential loop) running
```

If the data was already published by deploy time, the loop finishes in minutes — verify `CATCHUP_DONE` in `logs/deploy_regen.log` before step 9. If not yet published, the loop legitimately runs until ~02:45 server time; verify a poller process is alive, note it in the hand-off to the user, and proceed (this is our process doing the day's normal work, not deferred cleanup). Tomorrow's 21:00 cron fetches the NEXT date — no overlap.

### 7. Archive retrofit (~70k pages)

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc '/home/hatnote/virtualenvs/top3/bin/python /home/hatnote/top/top/retrofit_pages.py'"          # dry-run
```

Expect `would modify N` (tens of thousands), `already ok M` small (pages regenerated in steps 4/6), `no anchor K` small. If K > ~1% of total, inspect the reported sample paths before applying (pages lacking both `<meta charset="UTF-8">` and `<head>` are skipped by design). Then:

```bash
ssh wenli "sudo -n -H -u hatnote bash -lc '/home/hatnote/virtualenvs/top3/bin/python /home/hatnote/top/top/retrofit_pages.py --apply'"
ssh wenli "sudo -n -H -u hatnote bash -lc '/home/hatnote/virtualenvs/top3/bin/python /home/hatnote/top/top/retrofit_pages.py'"          # → would modify 0
```

### 8. Live-site checks (from laptop)

```bash
curl -s https://top.hatnote.com/robots.txt                                   # "User-agent: *" / "Allow: /"
curl -s https://top.hatnote.com/llms.txt | head -3                            # markdown, "# Hatnote Top 100"
curl -sI https://top.hatnote.com/js/top.js | head -1                          # 200
curl -s https://top.hatnote.com/ | grep -c 'application/ld+json'               # 1 (homepage, new pipeline)
curl -s https://top.hatnote.com/feeds/enwikipedia.rss | xmllint --noout - && echo LIVE_FEED_OK
curl -s https://top.hatnote.com/en/wikipedia/2016/5/1.html | grep -c viewport  # 1 (retrofit reached the archive; fixture regression-tested locally at 390/1280px)
```

### 9. USER ACTION — revoke passwordless sudo (must tell the user)

Report deployment status to the user (including whether a 6b catchup poller is still legitimately running), then tell them to run on wenli:

```bash
sudo rm /etc/sudoers.d/99-deploy-tmp
```

Agent verifies revocation: `ssh wenli 'sudo -n true 2>&1'` → must now FAIL with "a password is required". Post-revocation monitoring needs no sudo (mahmoud is in group `hatnote`): after the next 21:00 cron cycle, `ssh wenli 'tail -20 /home/hatnote/top/logs/cron_out/en.txt'` should show success (`S...`) lines and no traceback — optional user-side check, not part of this deployment's acceptance.

## Rollback

Requires sudo — perform before step 9's revocation, or have the user re-grant/run it.

1. Restore cron: `ssh wenli 'sudo -n crontab -u hatnote /home/mahmoud/hatnote-cron-backup.txt && sudo -n crontab -u hatnote -l | grep TOP_PYTHON_BIN'` (→ old `virtualenvs/top` path).
2. Revert code: `ssh wenli "sudo -n -H -u hatnote git -C /home/hatnote/top reset --hard <hash from step 3>"`.
3. Kill any top3 pollers/loops: `ssh wenli 'sudo -n -u hatnote pkill -f get_data.py'`; if a fetch day is incomplete, re-run the killed langs' cron command with the OLD venv (`/home/hatnote/virtualenvs/top/bin/python`).
4. Retrofitted viewport tags remain (not reversible); with chart.css reverted (`min-width: 500px` back) archived pages render the 500px layout scaled on phones — acceptable rollback state.
5. Pages regenerated in steps 4/6 stay new-format until re-run with the old venv (optional: re-run the same `--date` values per lang).

## Critical files & anchors

- `top/retrofit_pages.py` — retrofit CLI (dry-run default, `--apply`, `--root`); walks `BASE_PATH` = `/home/hatnote/top/static/` on the server.
- `top/build_page.py` `check_most_recent()` — source of `LATEST` in step 6a; returns newest date with data on disk.
- `top/get_data.py:473-486` — argparser proving cron's exact flags work under the py3 port.
- hatnote's crontab on wenli — the `TOP_PYTHON_BIN` line is the ONLY server edit outside the repo; backup at `/home/mahmoud/hatnote-cron-backup.txt`.
- `/etc/sudoers.d/99-deploy-tmp` — the temporary grant; MUST be gone at the end (step 9 verify).

## Verification

Inline per step. Final acceptance: (a) step 4 historical run passes all greps; (b) step 5 crontab shows top3 with a one-line diff; (c) step 6a reports `REGEN_DONE`, zero failures, homepage has JSON-LD; (d) step 6b (when applicable) shows `CATCHUP_DONE` or one live poller doing the day's normal fetch; (e) step 7 retrofit re-run reports 0; (f) step 8 live URLs all pass; (g) step 9 `sudo -n true` fails after the user revokes.

## Assumptions & contingencies

- **hatnote's GitHub SSH key works for `git pull`** (unverified — `/home/hatnote/.ssh` unreadable pre-sudo). Fallback: pull via public https URL.
- **lithoxyl 26.0.0 on python3.10**: verified on py3.14 locally, unverified on 3.10. If step 4 crashes inside lithoxyl: `pip install lithoxyl==21.1.0` into top3, re-run; if still failing → stop, Rollback, report.
- **Full 27-lang regen (6a)** re-fetches published (stable) pageview data and overwrites that date's json/html per lang — chosen so the whole site converts immediately and cron's first top3 run is routine, per the no-deferred-cleanup requirement.
- **Catchup log filenames**: 6b tees `bn` output to `bn.txt` while cron's typo'd entry uses `gn.txt` — harmless divergence, logs only.
- **Passwordless sudo scope**: full `NOPASSWD:ALL` in `/etc/sudoers.d/99-deploy-tmp` for simplicity (crontab needs root; hatnote steps need `-u hatnote`); lifetime is this deployment only, enforced by step 9's mandatory revoke-and-verify.
