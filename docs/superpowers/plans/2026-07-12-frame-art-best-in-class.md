# Frame TV "Best-in-Class Art Mode" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adopt TheFab21's Samsung TV integration as our new base and layer on the genuinely novel improvements nobody else has (four firmware-compat fixes, image dedup + sidecar map, upload type detection, batch throttle, WebSocket auto-reconnect), plus a browsable gallery UX and a presence-aware auto-art blueprint, then contribute each proven fix back upstream.

**Architecture:** P0 replaces the whole `custom_components/samsungtv_smart/` tree with TheFab21's pinned tag (tree-level copy, not a merge — histories are detached). All of our own changes concentrate in the vendored async Art client `api/art.py` plus a small `api/_dedup.py` helper, one read-only `media_source.py`, and a YAML blueprint — so future syncs from `fab21` stay cheap. Every risky change is proven by an automated regression test first, then deployed one build at a time to the real Frame TV.

**Tech Stack:** Python 3.13, Home Assistant custom integration (min HA 2025.7), aiohttp WebSocket + REST, Pillow (PIL) for image detection/dedup, pytest + pytest-asyncio for tests, git → Ark rsync + `docker restart homeassistant` for deploy.

## Global Constraints

Every task's requirements implicitly include this section. Exact values copied from the spec:

- **License:** base is **Apache-2.0** (retain C's `LICENSE` + `NOTICE`); `api/art.py` keeps its **`SPDX-License-Identifier: LGPL-3.0`** header + xchwarze/Garrett/Waterton attribution. Any LGPL code copied in keeps its header/attribution.
- **Min HA version:** `2025.7` — do not use APIs newer than that floor.
- **No committed `.pyc`:** the 17 committed `__pycache__/*.pyc` files are removed and gitignored; no new `.pyc` may be committed (criterion 15).
- **No pre-upload resize:** never add 16:9 / 3840×2160 conversion. The **only** PIL resize permitted is the 384×216 dedup thumbnail.
- **Change confinement:** all our code edits land in `custom_components/samsungtv_smart/api/art.py` + a small `api/_dedup.py` helper + `media_source.py` + a blueprint. Avoid editing `media_player.py`, `select.py`, `number.py`, etc. — every edit outside `art.py`/helpers is future merge-conflict debt against `fab21`.
- **Deploy path:** the ONLY deploy is git → Ark rsync of the component + `docker restart homeassistant`. No hand-editing on the server. The live install is only ever a checkout of a branch.
- **Serialized deploy lane:** exactly **one build is live on the TV at a time**. P2/P3/P4/P5 are authored in parallel on separate branches but integration-verified one at a time. Risky branches (P4 reconnect) get an isolated deploy slot.
- **Real test TVs (BOTH Frames):** there are **two** 65" Samsung Frames (model QN65LS03BAFXZA), each its own `samsungtv_smart` config entry, both on the single shared integration — **every TV-verify step runs against both**:
  - **Living Room** — config "Living Room TV (SmartThings)", host `192.168.1.64`, `media_player.living_room_tv`; art entities e.g. `switch.living_room_tv_art_mode`, `select.living_room_living_room_tv_matte_type`, `number.living_room_living_room_tv_art_mode_brightness`.
  - **Kitchen** — config "Kitchen TV (SmartThings)", host `192.168.1.140`, `media_player.kitchen_smartthings_hub` (naming quirk — **not** `media_player.kitchen_tv`); art entities e.g. `switch.kitchen_tv_art_mode`, `select.kitchen_kitchen_tv_matte_type`, `number.kitchen_kitchen_tv_art_mode_brightness`.
  Reached via `ssh ark`; HA is docker container `homeassistant` (`lscr.io/linuxserver/homeassistant`), config at host `/mnt/user/appdata/homeassistant`, log at `/mnt/user/appdata/homeassistant/home-assistant.log`.
- **Adopted base tag:** pin **`8.3.3`** (latest stable release; `8.4.0b*` are betas — do not pin a beta). Confirm it is still the latest stable at execution (Task 0.1) and record it in `docs/reference/adopted-base.md`.
- **Allowed noise:** HA's standard "custom integration" notice and the cosmetic "SmartThings report TV is off but status detected is on" warning are allowed; anything else in the log is a failure.

---

## Phase & parallelism map

- **P0 → P1 are strictly sequential and gate everything.** Do not start any P2+ task until P1's gate is green.
- After P1: **P2, P3, P4, P5 are authored in parallel on separate branches** (each branched off the P1 tip). They **share one serialized deploy lane** — merge + TV-verify one at a time.
- **P6** depends on P2's bug-1 fix landing; otherwise parallel with P3–P5.
- **P7** PRs each follow their source phase (P2/P3/P4) once that fix is TV-verified.
- Within P0: Task 0.2 (backup branch) runs in parallel with Task 0.1 (remote/tag). Within P1: Tasks 1.1/1.2 are parallel read-only.

Branch naming: `frame-art-best-in-class` is the integration branch. Author P2 on `p2-firmware-fixes`, P3 on `p3-dedup-upload`, P4 on `p4-reconnect`, P5 on `p5-gallery`, P6 on `p6-blueprint`. Each is cut from the P1 tip and merged back through the deploy lane.

---

## P0 — Safety, adopt base, deploy, smoke-verify _(sequential; gates all)_

### Task 0.1: Add `fab21` remote and pin the adopted base tag

**Files:**
- Create: `docs/reference/adopted-base.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a recorded, pinned git tag string `8.3.3` (or the confirmed-latest stable tag) that every later task's tree-copy references.

- [ ] **Step 1: Confirm the `fab21` remote exists and fetch its tags**

Run:
```bash
cd /Users/chansearrington/GitHub/personal/ha-samsungtv-smart
git remote -v | grep fab21
git fetch fab21 --tags
```
Expected: `fab21 https://github.com/TheFab21/ha-samsungtv-smart.git (fetch)` prints; fetch completes without error. (The remote is already configured in this repo.)

- [ ] **Step 2: Determine the latest STABLE release tag (exclude betas)**

Run:
```bash
git ls-remote --tags fab21 | grep -oE 'refs/tags/[0-9]+\.[0-9]+\.[0-9]+$' | sed 's#refs/tags/##' | sort -V | tail -1
```
Expected: `8.3.3`. (If a newer stable like `8.4.0` has since been released — i.e. a non-`b` tag greater than 8.3.3 — pin that instead. Never pin a `*b*` beta.)

- [ ] **Step 3: Record the pinned tag and its commit SHA**

Create `docs/reference/adopted-base.md`:
```markdown
# Adopted base (TheFab21 fork "C")

- **Upstream:** `fab21` = https://github.com/TheFab21/ha-samsungtv-smart.git
- **Pinned tag:** `8.3.3`
- **Pinned commit:** <output of `git rev-parse 8.3.3`>
- **Adopted on:** 2026-07-12
- **How to re-sync (deliberate only, never auto-pull):**
  `git fetch fab21 --tags` then re-run the Task 0.4 tree-copy against the new tag.
```
Fill `<output of ...>` by running `git rev-parse 8.3.3` and pasting the real SHA.

- [ ] **Step 4: Commit**

```bash
git add docs/reference/adopted-base.md
git commit -m "docs: pin adopted base to TheFab21 tag 8.3.3

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 0.2: Capture the live install (B) to a backup branch and prove restore _(parallel with 0.1)_

**Files:**
- Create: `docs/reference/backup-restore-runbook.md`

**Interfaces:**
- Consumes: `ssh ark` access; live install at `/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart`.
- Produces: git branch `backup/live-install-B` containing the exact bytes currently running on the TV; a proven restore procedure (satisfies criterion 3).

- [ ] **Step 1: Snapshot the live install off Ark into a fresh branch**

Run:
```bash
cd /Users/chansearrington/GitHub/personal/ha-samsungtv-smart
git checkout -b backup/live-install-B
rm -rf /tmp/ark-live-B && mkdir -p /tmp/ark-live-B
rsync -av --exclude='__pycache__' \
  ark:/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart/ \
  /tmp/ark-live-B/
rm -rf custom_components/samsungtv_smart
mkdir -p custom_components/samsungtv_smart
rsync -av /tmp/ark-live-B/ custom_components/samsungtv_smart/
git add -A custom_components/samsungtv_smart
git commit -m "chore: snapshot live install B (0.14.5) before adoption

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: a commit on `backup/live-install-B` capturing manifest version `0.14.5` (verify: `git show backup/live-install-B:custom_components/samsungtv_smart/manifest.json | grep version` prints `0.14.5`).

- [ ] **Step 2: Prove restore works (into a throwaway dir, non-destructively)**

Run:
```bash
rm -rf /tmp/restore-test && mkdir -p /tmp/restore-test
git archive backup/live-install-B custom_components/samsungtv_smart | tar -x -C /tmp/restore-test
diff -r /tmp/ark-live-B /tmp/restore-test/custom_components/samsungtv_smart --exclude='__pycache__'
echo "restore-diff-exit=$?"
```
Expected: `restore-diff-exit=0` (byte-identical restore). This proves we can put B back on the TV if a deploy fails.

- [ ] **Step 3: Write the restore runbook**

Create `docs/reference/backup-restore-runbook.md`:
```markdown
# Backup / restore runbook

**Backup branch:** `backup/live-install-B` = exact live install before adoption (manifest 0.14.5).

**To restore B onto the TV after a bad deploy:**
1. `git checkout backup/live-install-B`
2. `rsync -av --delete --exclude='__pycache__' custom_components/samsungtv_smart/ ark:/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart/`
3. `ssh ark 'docker restart homeassistant'`
4. Confirm `media_player.living_room_tv` returns (Task 0.6 smoke check).

Restore was proven byte-identical on 2026-07-12 via `git archive` + `diff -r`.
```

- [ ] **Step 4: Commit and return to the working branch**

```bash
git add docs/reference/backup-restore-runbook.md
git commit -m "docs: backup/restore runbook for live install B (restore proven)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git checkout frame-art-best-in-class
```

### Task 0.3: Repo hygiene — remove committed pyc, add `.gitignore`, stand up test scaffolding

**Files:**
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `requirements_test.txt`
- Create: `tests/__init__.py`, `tests/api/__init__.py`, `tests/conftest.py`
- Delete: all committed `custom_components/samsungtv_smart/**/__pycache__/*.pyc`

**Interfaces:**
- Consumes: nothing.
- Produces: a clean tree (no `.pyc`); a runnable `pytest` harness (`asyncio_mode = auto`) that all parallel P2–P5 branches inherit. Satisfies criterion 15's "no committed pyc" and enables every later test task.

- [ ] **Step 1: Remove the 17 committed pyc files and their `__pycache__` dirs**

Run:
```bash
cd /Users/chansearrington/GitHub/personal/ha-samsungtv-smart
git rm -r --cached $(git ls-files '*/__pycache__/*.pyc')
find custom_components -name '__pycache__' -type d -prune -exec rm -rf {} +
```
Expected: `git status` shows the pyc files staged for deletion; none remain on disk.

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/
*.bak
.DS_Store
```

- [ ] **Step 3: Create the pytest harness files**

`pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

`requirements_test.txt`:
```text
pytest>=8.0
pytest-asyncio>=0.23
Pillow>=10.0
aiohttp>=3.9
```

`tests/__init__.py`: (empty file)

`tests/api/__init__.py`: (empty file)

`tests/conftest.py`:
```python
"""Shared fixtures for Samsung Art client tests."""
import sys
from pathlib import Path

import pytest

# Make the vendored art client importable as a bare module.
API_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "samsungtv_smart" / "api"
sys.path.insert(0, str(API_DIR))


@pytest.fixture
def art_client():
    """A SamsungTVAsyncArt instance that never opens a real socket."""
    import art  # noqa: PLC0415

    client = art.SamsungTVAsyncArt(host="192.0.2.10", port=8002, token="tok", name="pytest")
    return client
```

- [ ] **Step 4: Verify the harness collects (proves scaffolding is valid before any test exists)**

Run:
```bash
python -m pytest tests/ --co -q
```
Expected: `no tests ran` (exit 5) with zero collection errors — the conftest imports cleanly.

- [ ] **Step 5: Commit**

```bash
git add -A .gitignore pytest.ini requirements_test.txt tests/
git rm -r --cached --ignore-unmatch $(git ls-files '*/__pycache__/*.pyc') 2>/dev/null; true
git add -A
git commit -m "chore: remove committed pyc, add gitignore and pytest scaffolding

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 0.4: Tree-level replace the component with the pinned base; retain license + re-apply docs

**Files:**
- Modify (full replace): `custom_components/samsungtv_smart/` (entire tree)
- Verify present: `custom_components/samsungtv_smart/LICENSE`, `NOTICE`, `api/art.py` (SPDX header)
- Re-apply: `README_CORRECTIONS.md`, `README_OAUTH2.md` (repo root)

**Interfaces:**
- Consumes: pinned tag `8.3.3` from Task 0.1.
- Produces: `custom_components/samsungtv_smart/` byte-equivalent to `fab21` tag `8.3.3`; manifest version `8.3.3`. Satisfies criterion 1.

- [ ] **Step 1: Replace the tree from the pinned tag**

Run:
```bash
cd /Users/chansearrington/GitHub/personal/ha-samsungtv-smart
rm -rf custom_components/samsungtv_smart
git checkout 8.3.3 -- custom_components/samsungtv_smart
find custom_components -name '__pycache__' -type d -prune -exec rm -rf {} +
```
Expected: the tree is now C's; `cat custom_components/samsungtv_smart/manifest.json | grep '"version"'` prints `"version": "8.3.3"`.

- [ ] **Step 2: Verify license + SPDX headers survived the copy**

Run:
```bash
test -f custom_components/samsungtv_smart/LICENSE && echo LICENSE_OK
test -f custom_components/samsungtv_smart/NOTICE && echo NOTICE_OK || echo NOTICE_MISSING
head -15 custom_components/samsungtv_smart/api/art.py | grep 'SPDX-License-Identifier: LGPL-3.0'
```
Expected: `LICENSE_OK`, the SPDX line prints. If `NOTICE_MISSING`, restore it from the tag: `git checkout 8.3.3 -- custom_components/samsungtv_smart/NOTICE` (only if it exists in the tag; if the tag has no NOTICE, record that in `docs/reference/adopted-base.md` and rely on `LICENSE` + per-file SPDX).

- [ ] **Step 3: Re-apply our two doc files if they are not already at root**

Run:
```bash
git checkout backup/live-install-B -- README_CORRECTIONS.md README_OAUTH2.md 2>/dev/null || \
  echo "doc files not in backup — skip (optional per spec)"
```
Expected: the two `README_*` files land at repo root, or the skip message (they are optional, spec §3).

- [ ] **Step 4: Confirm no stray pyc came in and the base-independent regions match the tag**

Run:
```bash
git ls-files '*/__pycache__/*.pyc' | wc -l
git checkout 8.3.3 -- custom_components/samsungtv_smart/api/art.py
git diff --stat 8.3.3 -- custom_components/samsungtv_smart/api/art.py
```
Expected: pyc count `0`; the `git diff --stat` against the tag for `art.py` shows **no differences** (proves byte-equivalence of the file our work will edit).

- [ ] **Step 5: Commit**

```bash
git add -A custom_components/samsungtv_smart README_CORRECTIONS.md README_OAUTH2.md 2>/dev/null; true
git add -A
git commit -m "feat: adopt TheFab21 base at tag 8.3.3 via tree-level replace

Retains Apache-2.0 LICENSE/NOTICE and LGPL-3.0 art.py header.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 0.5: Stand up the git → Ark deploy script

**Files:**
- Create: `scripts/deploy_to_ark.sh`

**Interfaces:**
- Consumes: `ssh ark`, the working tree under `custom_components/samsungtv_smart`.
- Produces: `scripts/deploy_to_ark.sh` — the ONLY deploy path (rsync component + restart container + tail log). Used by every "deploy + TV-verify" task.

- [ ] **Step 1: Write the deploy script**

`scripts/deploy_to_ark.sh`:
```bash
#!/usr/bin/env bash
# The ONLY way to deploy this component to the live TV.
# Usage: scripts/deploy_to_ark.sh
set -euo pipefail

LOCAL="$(cd "$(dirname "$0")/.." && pwd)/custom_components/samsungtv_smart/"
REMOTE="ark:/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart/"
LOG="/mnt/user/appdata/homeassistant/home-assistant.log"

echo ">> rsync $LOCAL -> $REMOTE"
rsync -av --delete --exclude='__pycache__' --exclude='*.pyc' "$LOCAL" "$REMOTE"

echo ">> restarting homeassistant container"
ssh ark 'docker restart homeassistant'

echo ">> waiting 45s for HA to come up"
sleep 45

echo ">> scanning log for samsungtv errors (last 400 lines)"
ssh ark "tail -n 400 $LOG | grep -iE 'error|traceback|exception' | grep -i samsungtv" \
  && { echo '!! samsungtv errors found in log'; exit 1; } \
  || echo '>> no samsungtv errors in recent log'
```

- [ ] **Step 2: Make it executable and dry-run the rsync (no changes pushed)**

Run:
```bash
cd /Users/chansearrington/GitHub/personal/ha-samsungtv-smart
chmod +x scripts/deploy_to_ark.sh
rsync -avn --delete --exclude='__pycache__' --exclude='*.pyc' \
  custom_components/samsungtv_smart/ \
  ark:/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart/
```
Expected: the `-n` dry-run lists files that WOULD transfer (the 8.3.3 tree replacing 0.14.5) without changing anything on Ark.

- [ ] **Step 3: Commit**

```bash
git add scripts/deploy_to_ark.sh
git commit -m "chore: add git->Ark deploy script (rsync + restart + log scan)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 0.6: Deploy the adopted base and smoke-verify on the real TV

**Files:**
- Create: `docs/reference/p0-smoke-note.md`

**Interfaces:**
- Consumes: `scripts/deploy_to_ark.sh`; backup branch from Task 0.2.
- Produces: a live, clean install of the 8.3.3 base with `media_player.living_room_tv` present. Satisfies criteria 2, 4 (and closes 1, 3).

- [ ] **Step 1: Deploy**

Run:
```bash
cd /Users/chansearrington/GitHub/personal/ha-samsungtv-smart
scripts/deploy_to_ark.sh
```
Expected: script ends with `>> no samsungtv errors in recent log`. (Watch the physical Frame during this deploy — if the IP-control channel prompts to accept a new pairing, accept it once on the TV, per spec open-question 2 / risk table.)

- [ ] **Step 2: Confirm the integration loaded with only allowed noise (criterion 2)**

Run:
```bash
ssh ark "grep -iE 'samsungtv' /mnt/user/appdata/homeassistant/home-assistant.log | grep -ivE 'custom integration|SmartThings report TV is off but status detected is on' | grep -iE 'error|warning|traceback'"
echo "unexpected-log-lines-exit=$?"
```
Expected: `unexpected-log-lines-exit=1` (grep found nothing → only the allowed "custom integration" notice and the cosmetic SmartThings warning are present).

- [ ] **Step 3: Confirm `media_player.living_room_tv` is present and controllable (criterion 4)**

Run (via HA CLI inside the container):
```bash
ssh ark "docker exec homeassistant python -c \"import homeassistant\" 2>/dev/null; docker exec homeassistant ha state get media_player.living_room_tv" 2>/dev/null \
  || ssh ark "grep -i 'media_player.living_room_tv' /mnt/user/appdata/homeassistant/home-assistant.log | tail -3"
```
Expected: the entity resolves to a real state (e.g. `on`/`off`/`playing`), proving it survived the migration. Then exercise a harmless control and read it back:
```bash
# Use the HA REST API or Developer Tools; example via curl from Ark (token in HA):
ssh ark "curl -s -X POST -H 'Authorization: Bearer \$HA_TOKEN' -H 'Content-Type: application/json' \
  http://localhost:8123/api/services/media_player/volume_up -d '{\"entity_id\":\"media_player.living_room_tv\"}'"
```
Expected: HTTP 200; TV volume nudges (or a benign no-op if off) with no error in the log. (If `$HA_TOKEN` is not set on Ark, drive the same service from HA Developer Tools → Actions instead and record the result.)

- [ ] **Step 4: Write the smoke note (records criteria 1–4 status)**

Create `docs/reference/p0-smoke-note.md` capturing: pinned tag deployed (`8.3.3`), log clean (yes/no), `media_player.living_room_tv` present (yes/no), IP-control pairing prompt seen (yes/no + accepted), backup branch name. Fill with the real observed values.

- [ ] **Step 5: Commit**

```bash
git add docs/reference/p0-smoke-note.md
git commit -m "docs: P0 smoke-verify note (base 8.3.3 live, TV present, log clean)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P0 GATE:** criteria 1, 2, 3, 4 pass. Do not proceed until green.

---

## P1 — Baseline-verify C's features on the real TV _(sequential; gates P2–P4)_

### Task 1.1: Verify the art dropdown populates and selection changes the TV _(parallel read-only with 1.2)_

**Files:**
- Create: `docs/reference/p1-baseline-note.md` (section: art dropdown)

**Interfaces:**
- Consumes: live 8.3.3 install; **both Frames** (`media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`).
- Produces: recorded evidence that the art-select entity lists ≥ 10 artworks and selection lands within 10 s **on each Frame**. Satisfies criterion 5.

> **Both Frames:** run every step below for the living-room Frame AND the kitchen Frame; record each TV's entity ids and results separately (criterion 5 passes only when both do).

- [ ] **Step 1: Find the art-selection entity for the Frame**

Run:
```bash
ssh ark "grep -oiE 'select\.[a-z0-9_]*art[a-z0-9_]*' /mnt/user/appdata/homeassistant/home-assistant.log | sort -u"
```
Expected: the art-select entity id (e.g. `select.living_room_tv_art` — record the exact id). If nothing matches, list all selects for the device via HA Developer Tools → States, filter by the TV's device.

- [ ] **Step 2: Confirm ≥ 10 options and record them**

In HA Developer Tools → States, open the art-select entity; count `options`.
Expected: `options` length **≥ 10**. Record the count and the first 3 content ids in the baseline note.

- [ ] **Step 3: Select an artwork and time the change (≤ 10 s)**

In HA Developer Tools → Actions, call `select.select_option` with a different `current_option`, start a stopwatch, and observe the physical Frame (or re-read `current_option` / `get_current` art).
Expected: the displayed art changes within **10 s**. Record the observed latency.

- [ ] **Step 4: Write the art-dropdown section of the baseline note and commit**

Create/append `docs/reference/p1-baseline-note.md` with the entity id, option count, and observed selection latency. Then:
```bash
git add docs/reference/p1-baseline-note.md
git commit -m "docs: P1 baseline — art dropdown populated and selection verified

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 1.2: Verify C's platforms instantiate (selects, numbers, button, thumbnail, token-notify) _(parallel read-only with 1.1)_

**Files:**
- Modify: `docs/reference/p1-baseline-note.md` (section: platforms)

**Interfaces:**
- Consumes: live install; **both Frames** (`media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`).
- Produces: recorded evidence that the 11 selects, 5 numbers, Reboot-TV button, thumbnail HTTP view, and token-notify all instantiate without error **on each Frame**. Satisfies criterion 6.

> **Both Frames:** confirm the platform set on the living-room Frame AND the kitchen Frame (note the kitchen entity ids use the `kitchen_kitchen_tv_*` / `kitchen_tv_*` prefixes); criterion 6 passes only when both do.

- [ ] **Step 1: Count the TV's select and number entities**

In HA Developer Tools → States filtered to the Frame's device (or via the log), confirm **11 selects** (Color Tone, Speaker Output, SmartThings Media Output, Matte Type, Matte Color, Picture Mode, Art Motion Sensitivity, Art Motion Timer, Art Brightness Sensor, …) and **5 numbers** (IP Backlight 0–50, IP Picture, Art Brightness 0–100, Art Color Temperature −5..+5).
Expected: counts match; record any that are missing or errored.

- [ ] **Step 2: Confirm the Reboot-TV button and token-notify exist and errored-free**

Run:
```bash
ssh ark "grep -iE 'button\.[a-z0-9_]*reboot|token' /mnt/user/appdata/homeassistant/home-assistant.log | grep -iE 'error|traceback'"
echo "platform-errors-exit=$?"
```
Expected: `platform-errors-exit=1` (no errors). Confirm a reboot button entity exists in States (do NOT press it here).

- [ ] **Step 3: Confirm the thumbnail HTTP view serves an image (no base64)**

Run (from Ark, hitting the registered view):
```bash
ssh ark "curl -s -o /dev/null -w '%{http_code} %{content_type}\n' 'http://localhost:8123/api/samsungtv_smart/thumbnail?path=<a_real_content_id>&w=200'"
```
Expected: `200 image/jpeg` (substitute a real content id from Task 1.1). Records that previews come from the HTTP view, not base64.

- [ ] **Step 4: Write the platforms section and commit**

Append to `docs/reference/p1-baseline-note.md`, then:
```bash
git add docs/reference/p1-baseline-note.md
git commit -m "docs: P1 baseline — 11 selects, 5 numbers, button, thumbnail view verified

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 1.3: Record which of the four firmware bugs actually reproduce on this panel

**Files:**
- Modify: `docs/reference/p1-baseline-note.md` (section: firmware-bug reproduction)

**Interfaces:**
- Consumes: live install; the four bug descriptions (spec §2.7–2.10 / digest §5).
- Produces: a per-bug "reproduces live: yes/no" record. Bugs that do not reproduce live still ship with automated regression tests as proof (risk table). Feeds P2.

> **Both Frames:** check bug reproduction on the living-room Frame AND the kitchen Frame — a bug (esp. bug 1 art-mode misdetection, bug 2 matte list) may reproduce on one Frame and not the other; record each per-TV.

- [ ] **Step 1: Bug 1 (art-mode misdetection) — put the TV in Art Mode and check REST vs report**

Put the Frame into Art Mode. Read the TV's REST device object and the integration's art-mode report:
```bash
ssh ark "curl -s http://<frame-ip>:8001/api/v2/ | python3 -c 'import sys,json;print(json.load(sys.stdin)[\"device\"][\"PowerState\"])'"
```
Expected: note whether REST prints `standby` while the panel is showing art (that is the bug). Record yes/no. (Frame IP is in the integration config; read it from the log or config entry.)

- [ ] **Step 2: Bug 2 (matte list empty) — read the Matte Type select options**

In States, open the Matte Type select for the Frame.
Expected: record whether its `options` list is empty (bug reproduces) or populated. Record yes/no.

- [ ] **Step 3: Bugs 3 & 4 — record as test-only if not observable live**

Bug 3 (art-status `status` vs `value`) and bug 4 (upload type) are payload/firmware-shape bugs. If they cannot be forced on this panel, record "test-only proof" — they will still ship with regression tests (criterion 15 / risk table).

- [ ] **Step 4: Write the reproduction table and commit**

Append a 4-row table (bug | reproduces live | how observed) to `docs/reference/p1-baseline-note.md`, then:
```bash
git add docs/reference/p1-baseline-note.md
git commit -m "docs: P1 baseline — firmware-bug live-reproduction record

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P1 GATE:** criteria 5, 6 pass; baseline note records which bugs reproduce. Do not start P2–P5 until green. After this, cut branches `p2-firmware-fixes`, `p3-dedup-upload`, `p4-reconnect`, `p5-gallery` from this tip.

---

## P2 — Firmware-compat fixes (bugs 1–4) with tests _(parallel-authored on `p2-firmware-fixes`)_

All four fixes edit the adopted `api/art.py`. Author them in parallel; merge + TV-verify through the one deploy lane in Task 2.5.

> **Note on Step 1 of every P2/P3/P4/P5 code task — "researcher lock-in".** P0 replaced the base file, so exact line numbers are legitimately deferred to execution (they are NOT placeholders). Step 1 = open the *adopted* `api/art.py` (post-P0), locate the named method, and record its real line range + confirm the logger name (`self._log` vs module `_LOGGER`) and exact signature before editing. Test code below is base-independent (it patches methods / feeds payloads) and is fully concrete.

### Task 2.1: Bug 1 — three-tier `on()` / `is_artmode()` / `in_artmode()`

**Files:**
- Modify: `custom_components/samsungtv_smart/api/art.py` (methods `on()`, `is_artmode()`; add `in_artmode()`)
- Test: `tests/api/test_art_bug1_artmode_detection.py`

**Interfaces:**
- Consumes: `SamsungTVAsyncArt.on() -> bool` (REST PowerState), `SamsungTVAsyncArt.get_artmode() -> str | None` (art-WS `get_artmode_status`), `self.art_mode: bool | None` (cached event flag).
- Produces: `async def in_artmode(self) -> bool` = authoritative art-mode check = `await self.on() or (await self.get_artmode()) == "on"`. `is_artmode()` keeps returning cached `self.art_mode`. Later tasks and P6 blueprint rely on `in_artmode()`.

- [ ] **Step 1: Researcher lock-in** — open `custom_components/samsungtv_smart/api/art.py`; record the real line range of `on()` and `is_artmode()` (in the 8.3.3 tag these were ~L792 and ~L807). Confirm `get_artmode()` exists (~L1289) and returns the raw `"on"`/`"off"` string, and that `self.art_mode` is the cached flag set in `_process_event`.

- [ ] **Step 2: Write the failing test**

`tests/api/test_art_bug1_artmode_detection.py`:
```python
"""Bug 1: 2025 Frame reports REST PowerState=standby while Art Mode is ON."""
import pytest


async def test_in_artmode_true_when_rest_standby_but_artws_on(art_client, monkeypatch):
    # REST says the TV is off/standby (the live bug on TQ50LS03FAUXXC)...
    async def fake_on():
        return False

    # ...but the Art WebSocket authoritatively reports art mode on.
    async def fake_get_artmode():
        return "on"

    monkeypatch.setattr(art_client, "on", fake_on)
    monkeypatch.setattr(art_client, "get_artmode", fake_get_artmode)

    assert await art_client.in_artmode() is True


async def test_in_artmode_true_when_rest_on(art_client, monkeypatch):
    async def fake_on():
        return True

    async def fake_get_artmode():
        return "off"

    monkeypatch.setattr(art_client, "on", fake_on)
    monkeypatch.setattr(art_client, "get_artmode", fake_get_artmode)

    assert await art_client.in_artmode() is True


async def test_in_artmode_false_when_both_off(art_client, monkeypatch):
    async def fake_on():
        return False

    async def fake_get_artmode():
        return "off"

    monkeypatch.setattr(art_client, "on", fake_on)
    monkeypatch.setattr(art_client, "get_artmode", fake_get_artmode)

    assert await art_client.in_artmode() is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_art_bug1_artmode_detection.py -v`
Expected: FAIL — `AttributeError: 'SamsungTVAsyncArt' object has no attribute 'in_artmode'`.

- [ ] **Step 4: Write minimal implementation** — add the new method next to `is_artmode()` in `art.py`:

```python
    async def in_artmode(self) -> bool:
        """Authoritative art-mode check.

        Trust the Art WebSocket (get_artmode_status), not REST PowerState:
        2025 Frames report PowerState="standby" while Art Mode is ON.
        """
        if await self.on():
            return True
        return (await self.get_artmode()) == "on"
```
(Leave `on()` and `is_artmode()` as-is; `in_artmode()` is the new authoritative gate callers should use.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_art_bug1_artmode_detection.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/api/test_art_bug1_artmode_detection.py custom_components/samsungtv_smart/api/art.py
git commit -m "fix(art): bug 1 — add in_artmode() trusting art-WS over REST standby

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 2.2: Bug 2 — `get_matte_list()` reads `matte_list` OR `matte_type_list`

**Files:**
- Modify: `custom_components/samsungtv_smart/api/art.py` (method `get_matte_list()`)
- Test: `tests/api/test_art_bug2_matte_list.py`

**Interfaces:**
- Consumes: `SamsungTVAsyncArt._send_art_request(request_data: dict) -> dict | None`.
- Produces: `get_matte_list(include_color: bool = False) -> list | tuple` returns a non-empty list when the payload uses **either** `matte_list` (newer firmware) or `matte_type_list` (older).

- [ ] **Step 1: Researcher lock-in** — record the real line range of `get_matte_list()` (8.3.3 ~L1394) and confirm it currently reads only `data.get("matte_type_list", "[]")`.

- [ ] **Step 2: Write the failing test**

`tests/api/test_art_bug2_matte_list.py`:
```python
"""Bug 2: field matte_type_list was renamed matte_list on some firmware."""
import json


async def test_matte_list_new_field_name(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"matte_list": json.dumps(["none", "shadowbox_polar", "modernthin_black"])}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    result = await art_client.get_matte_list()
    assert result == ["none", "shadowbox_polar", "modernthin_black"]


async def test_matte_list_old_field_name(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"matte_type_list": json.dumps(["none", "flexible_polar"])}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    result = await art_client.get_matte_list()
    assert result == ["none", "flexible_polar"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_art_bug2_matte_list.py -v`
Expected: `test_matte_list_new_field_name` FAILS (returns `[]` because only `matte_type_list` is read); `test_matte_list_old_field_name` passes.

- [ ] **Step 4: Write minimal implementation** — change the field read in `get_matte_list()`:

```python
            matte_types = data.get("matte_list", data.get("matte_type_list", "[]"))
```
(Leave the `json.loads` parsing and the `include_color` branch unchanged.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_art_bug2_matte_list.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/api/test_art_bug2_matte_list.py custom_components/samsungtv_smart/api/art.py
git commit -m "fix(art): bug 2 — get_matte_list reads matte_list or matte_type_list

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 2.3: Bug 3 — `get_artmode()` reads `value` OR `status`

**Files:**
- Modify: `custom_components/samsungtv_smart/api/art.py` (method `get_artmode()`)
- Test: `tests/api/test_art_bug3_artmode_field.py`

**Interfaces:**
- Consumes: `_send_art_request`.
- Produces: `get_artmode() -> str | None` returns `"on"`/`"off"` correctly when the payload is keyed `value` (older) OR `status` (API 5.x); also updates cached `self.art_mode`.

- [ ] **Step 1: Researcher lock-in** — record the real line range of `get_artmode()` (8.3.3 ~L1289); confirm it currently does `value = data.get("value")` and sets `self.art_mode = value == "on"`.

- [ ] **Step 2: Write the failing test**

`tests/api/test_art_bug3_artmode_field.py`:
```python
"""Bug 3: API 5.x uses 'status' instead of 'value' for art-mode state."""


async def test_get_artmode_value_field(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"value": "on"}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    assert await art_client.get_artmode() == "on"
    assert art_client.art_mode is True


async def test_get_artmode_status_field(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {"status": "on"}  # API 5.x shape, no 'value' key

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    assert await art_client.get_artmode() == "on"
    assert art_client.art_mode is True


async def test_get_artmode_defaults_off(art_client, monkeypatch):
    async def fake_send(request_data, *a, **k):
        return {}

    monkeypatch.setattr(art_client, "_send_art_request", fake_send)
    assert await art_client.get_artmode() == "off"
    assert art_client.art_mode is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_art_bug3_artmode_field.py -v`
Expected: `test_get_artmode_status_field` and `test_get_artmode_defaults_off` FAIL (returns `None` when `value` is absent).

- [ ] **Step 4: Write minimal implementation** — in `get_artmode()` change the value read:

```python
            value = data.get("value", data.get("status", "off"))
            self.art_mode = value == "on"
            return value
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_art_bug3_artmode_field.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/api/test_art_bug3_artmode_field.py custom_components/samsungtv_smart/api/art.py
git commit -m "fix(art): bug 3 — get_artmode reads value or status field

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 2.4: Bug 4 — upload type detection via PIL (`jpg`/`png`/`mpo`)

**Files:**
- Modify: `custom_components/samsungtv_smart/api/art.py` (add `_detect_wire_type()`, call it in `upload()`)
- Test: `tests/api/test_art_bug4_upload_type.py`

**Interfaces:**
- Consumes: Pillow (`PIL.Image`).
- Produces: `def _detect_wire_type(data: bytes, hint: str | None = None) -> str` — opens the bytes with PIL, reads `.format`, maps `JPEG`/`MPO` → `"jpg"`, `PNG` → `"png"`; falls back to the `hint` (normalized, `jpeg`→`jpg`) only if PIL can't identify. `upload()` uses it for `bytes` inputs so a wrong caller hint is overridden. **Coordinate with P3** — this is the single shared upload-type-detection implementation.

- [ ] **Step 1: Researcher lock-in** — record the real line range of `upload()` (8.3.3 ~L1720); confirm it defaults `file_type="png"`, derives type from extension for `str` paths, and already maps `jpeg`→`jpg`. Confirm `from PIL import Image` import location (add at top of file if absent).

- [ ] **Step 2: Write the failing test**

`tests/api/test_art_bug4_upload_type.py`:
```python
"""Bug 4: detect real image format via PIL; send 'jpg' (not 'jpeg') on the wire."""
import io

import pytest
from PIL import Image


def _jpeg_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (10, 20, 30)).save(buf, format="JPEG")
    return buf.getvalue()


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (40, 50, 60)).save(buf, format="PNG")
    return buf.getvalue()


def _mpo_bytes():
    # An MPO is JPEG-family; PIL reports format 'MPO'. Fake by tagging JPEG bytes
    # as MPO via a second frame is heavy — instead assert the jpeg-family mapping
    # by patching PIL to report 'MPO' is out of scope; use real JPEG whose format
    # maps identically, plus a direct format-string check below.
    return _jpeg_bytes()


def test_detect_jpeg(art_client):
    import art
    assert art._detect_wire_type(_jpeg_bytes(), hint="png") == "jpg"


def test_detect_png(art_client):
    import art
    assert art._detect_wire_type(_png_bytes(), hint="jpeg") == "png"


def test_detect_maps_mpo_and_jpeg_family_to_jpg(art_client):
    import art
    # format-string mapping is the load-bearing rule for MPO/JPEG family
    assert art._map_format_to_wire("MPO") == "jpg"
    assert art._map_format_to_wire("JPEG") == "jpg"
    assert art._map_format_to_wire("PNG") == "png"


def test_wrong_caller_hint_overridden(art_client):
    import art
    # Caller lied and said png, bytes are really JPEG -> detection wins.
    assert art._detect_wire_type(_jpeg_bytes(), hint="png") == "jpg"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_art_bug4_upload_type.py -v`
Expected: FAIL — `AttributeError: module 'art' has no attribute '_detect_wire_type'`.

- [ ] **Step 4: Write minimal implementation** — add module-level helpers to `art.py` (after imports; ensure `from PIL import Image` and `import io` are present):

```python
def _map_format_to_wire(pil_format: str | None) -> str | None:
    """Map a PIL image format to the Samsung wire file_type."""
    if not pil_format:
        return None
    fmt = pil_format.upper()
    if fmt in ("JPEG", "JPG", "MPO"):
        return "jpg"
    if fmt == "PNG":
        return "png"
    return fmt.lower()


def _detect_wire_type(data: bytes, hint: str | None = None) -> str:
    """Detect the real image format from bytes; fall back to the caller hint."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            wire = _map_format_to_wire(img.format)
            if wire:
                return wire
    except Exception:  # noqa: BLE001 - detection is best-effort; fall back to hint
        pass
    normalized = (hint or "png").lower()
    return "jpg" if normalized in ("jpg", "jpeg", "mpo") else normalized
```
Then in `upload()`, after `file` has been resolved to bytes and before building the request, replace the plain `file_type` handling with a detection call:
```python
        file_size = len(file)
        file_type = _detect_wire_type(file, hint=file_type)
```
(This supersedes the existing `if file_type == "jpeg": file_type = "jpg"` line — remove that now-redundant line.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_art_bug4_upload_type.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/api/test_art_bug4_upload_type.py custom_components/samsungtv_smart/api/art.py
git commit -m "fix(art): bug 4 — detect upload type via PIL, send jpg on wire

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 2.5: P2 deploy + TV-verify (serialized deploy lane)

**Files:**
- Modify: `docs/reference/p2-verify-note.md` (create)

**Interfaces:**
- Consumes: all four fixes on `p2-firmware-fixes`; `scripts/deploy_to_ark.sh`; backup branch.
- Produces: TV-verified proof of criteria 7, 8, 9, 10, plus 15 (tests green, no pyc) and 16 (no regression of 4–6). **TV-verify runs against both Frames: `media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`.**

- [ ] **Step 1: Full test suite green + no pyc (criterion 15)**

Run:
```bash
python -m pytest tests/ -v
git ls-files '*/__pycache__/*.pyc' | wc -l
```
Expected: all tests pass; pyc count `0`.

- [ ] **Step 2: Take the deploy lane, merge to integration branch, deploy**

Run:
```bash
git checkout frame-art-best-in-class
git merge --no-ff p2-firmware-fixes -m "merge: P2 firmware-compat fixes (bugs 1-4)"
scripts/deploy_to_ark.sh
```
Expected: deploy ends with `>> no samsungtv errors in recent log`.

- [ ] **Step 3: TV-verify each fix (criteria 7, 8, 9, 10)**

- Criterion 7 (bug 1): put the Frame in Art Mode with REST reporting standby; confirm the integration now reports in-art-mode true (art-select/upload no longer refused). Cross-checked by the passing regression test in Step 1.
- Criterion 8 (bug 2): open the Matte Type select — `options` is non-empty on the real TV.
- Criterion 9 (bug 3): regression test is the proof (field-shape bug, may be test-only per P1.3).
- Criterion 10 (bug 4): upload a real JPEG, a PNG, and an MPO via the upload service; confirm each lands (no `send_image` error in the log) — the wire type is `jpg` for the JPEG/MPO.

- [ ] **Step 4: Regression check (criterion 16)** — re-run the Task 1.1/1.2 checks: art dropdown still ≥ 10 options and selection ≤ 10 s; 11 selects + 5 numbers still present. Record in the verify note.

- [ ] **Step 5: Write the verify note and commit**

Create `docs/reference/p2-verify-note.md` with per-criterion pass/fail + observed evidence, then:
```bash
git add docs/reference/p2-verify-note.md
git commit -m "docs: P2 TV-verify note (criteria 7-10, 15, 16)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P2 GATE:** criteria 7, 8, 9, 10, 15, 16 pass.

---

## P3 — Dedup + sidecar map + upload type detection + batch throttle _(parallel-authored on `p3-dedup-upload`)_

Upload type detection is implemented once in Task 2.4 (`_detect_wire_type`); P3 consumes it, does not re-implement it.

### Task 3.1: Perceptual dedup helper (`_dedup.py`)

**Files:**
- Create: `custom_components/samsungtv_smart/api/_dedup.py`
- Test: `tests/api/test_dedup_perceptual.py`

**Interfaces:**
- Consumes: Pillow (`Image`, `ImageChops`, `ImageFilter`).
- Produces: `def perceptual_diff(img_a: bytes, img_b: bytes) -> float` (grayscale → `resize((384, 216))` → `GaussianBlur(2)` → `ImageChops.difference` → normalized mean 0–255 scaled so identical-after-reencode ≤ 1.0); `def is_duplicate(img_a: bytes, img_b: bytes, threshold: float = 1.0) -> bool`.

- [ ] **Step 1: Researcher lock-in** — confirm no dedup logic already exists in the adopted `api/art.py` (grep for `GaussianBlur`, `ImageChops`, `perceptual`). If the adopted base added any, note it and adapt rather than duplicate.

- [ ] **Step 2: Write the failing test**

`tests/api/test_dedup_perceptual.py`:
```python
"""Perceptual dedup: TV re-encodes uploads, so exact hashes never match."""
import io

from PIL import Image


def _img(color, fmt="PNG", size=(400, 300)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def _reencoded(color):
    # Same picture, re-saved as JPEG (what the TV does) -> bytes differ, image same.
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), color).save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def test_same_image_reencoded_is_duplicate():
    import _dedup
    a = _img((120, 80, 40))
    b = _reencoded((120, 80, 40))
    assert _dedup.perceptual_diff(a, b) <= 1.0
    assert _dedup.is_duplicate(a, b) is True


def test_different_images_not_duplicate():
    import _dedup
    a = _img((10, 10, 10))
    b = _img((240, 240, 240))
    assert _dedup.perceptual_diff(a, b) > 1.0
    assert _dedup.is_duplicate(a, b) is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_dedup_perceptual.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named '_dedup'`.

- [ ] **Step 4: Write minimal implementation**

`custom_components/samsungtv_smart/api/_dedup.py`:
```python
"""Perceptual dedup + content_id sidecar map for the Samsung Art client.

SPDX-License-Identifier: LGPL-3.0
Dedup approach adapted from NickWaterton async_art_gallery_web.py (LGPL).
"""
from __future__ import annotations

import io

from PIL import Image, ImageChops, ImageFilter

_THUMB_SIZE = (384, 216)


def _fingerprint(data: bytes) -> Image.Image:
    with Image.open(io.BytesIO(data)) as img:
        return (
            img.convert("L")
            .resize(_THUMB_SIZE)
            .filter(ImageFilter.GaussianBlur(2))
        )


def perceptual_diff(img_a: bytes, img_b: bytes) -> float:
    """Return mean per-pixel grayscale difference (0-255) of two images."""
    fa = _fingerprint(img_a)
    fb = _fingerprint(img_b)
    diff = ImageChops.difference(fa, fb)
    hist = diff.histogram()
    total = sum(i * n for i, n in enumerate(hist))
    count = sum(hist)
    return total / count if count else 0.0


def is_duplicate(img_a: bytes, img_b: bytes, threshold: float = 1.0) -> bool:
    """True if two images are perceptually identical (survives TV re-encode)."""
    return perceptual_diff(img_a, img_b) <= threshold
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_dedup_perceptual.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/samsungtv_smart/api/_dedup.py tests/api/test_dedup_perceptual.py
git commit -m "feat(art): perceptual dedup helper (384x216 grayscale blur diff)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 3.2: content_id sidecar map — skip unchanged, never touch `SAM-F####`/`MY-F####`

**Files:**
- Modify: `custom_components/samsungtv_smart/api/_dedup.py` (add sidecar functions)
- Test: `tests/api/test_dedup_sidecar.py`

**Interfaces:**
- Consumes: `_dedup` module.
- Produces: `def load_sidecar(path: str) -> dict`; `def save_sidecar(path: str, data: dict) -> None`; `def needs_upload(filename: str, mtime: float, sidecar: dict) -> bool` (True only if new or mtime changed); `def is_protected(content_id: str) -> bool` (True for `SAM-F####` Samsung-Store and `MY-F####` other-tools art — never delete/modify). Sidecar shape: `{filename: {"content_id": str, "modified": float}}`.

- [ ] **Step 1: Researcher lock-in** — confirm `_dedup.py` from Task 3.1 exists on this branch (rebase/merge `p3` tasks in order) and grep the adopted `art.py` for any existing sidecar/`content_id` map to avoid duplication.

- [ ] **Step 2: Write the failing test**

`tests/api/test_dedup_sidecar.py`:
```python
"""Sidecar map: skip unchanged files; never touch Samsung-Store / other-tools art."""
import json


def test_needs_upload_new_file():
    import _dedup
    sidecar = {}
    assert _dedup.needs_upload("cat.jpg", mtime=100.0, sidecar=sidecar) is True


def test_needs_upload_unchanged_file_skipped():
    import _dedup
    sidecar = {"cat.jpg": {"content_id": "MY-F0001", "modified": 100.0}}
    assert _dedup.needs_upload("cat.jpg", mtime=100.0, sidecar=sidecar) is False


def test_needs_upload_changed_mtime():
    import _dedup
    sidecar = {"cat.jpg": {"content_id": "MY-F0001", "modified": 100.0}}
    assert _dedup.needs_upload("cat.jpg", mtime=200.0, sidecar=sidecar) is True


def test_is_protected_samsung_store_and_other_tools():
    import _dedup
    assert _dedup.is_protected("SAM-F0042") is True   # Samsung Store
    assert _dedup.is_protected("MY-F0007") is True     # another tool's art
    # Our own uploads use plain content ids we recorded ourselves — not protected.
    assert _dedup.is_protected("") is False


def test_sidecar_roundtrip(tmp_path):
    import _dedup
    p = str(tmp_path / "sidecar.json")
    data = {"cat.jpg": {"content_id": "abc", "modified": 1.0}}
    _dedup.save_sidecar(p, data)
    assert _dedup.load_sidecar(p) == data
    assert json.loads((tmp_path / "sidecar.json").read_text()) == data


def test_load_sidecar_missing_returns_empty(tmp_path):
    import _dedup
    assert _dedup.load_sidecar(str(tmp_path / "nope.json")) == {}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_dedup_sidecar.py -v`
Expected: FAIL — `AttributeError: module '_dedup' has no attribute 'needs_upload'`.

- [ ] **Step 4: Write minimal implementation** — append to `_dedup.py`:

```python
import json
import os

# Samsung-Store art is SAM-F####; other tools' uploads are MY-F####. Never modify.
_PROTECTED_PREFIXES = ("SAM-F", "MY-F")


def load_sidecar(path: str) -> dict:
    """Load the content_id sidecar map, or {} if it does not exist."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_sidecar(path: str, data: dict) -> None:
    """Persist the content_id sidecar map."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def needs_upload(filename: str, mtime: float, sidecar: dict) -> bool:
    """True if the file is new or its mtime changed since the last upload."""
    entry = sidecar.get(filename)
    if not entry:
        return True
    return entry.get("modified") != mtime


def is_protected(content_id: str) -> bool:
    """True for Samsung-Store (SAM-F####) or other-tools (MY-F####) art."""
    return content_id.startswith(_PROTECTED_PREFIXES)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_dedup_sidecar.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/samsungtv_smart/api/_dedup.py tests/api/test_dedup_sidecar.py
git commit -m "feat(art): content_id sidecar map + protected-prefix guard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 3.3: Batch upload throttle (~2 s spacing) + sidecar-aware skip

**Files:**
- Modify: `custom_components/samsungtv_smart/api/art.py` (add `upload_batch()` + `_UPLOAD_THROTTLE_SECONDS`)
- Test: `tests/api/test_art_batch_throttle.py`

**Interfaces:**
- Consumes: `SamsungTVAsyncArt.upload(...) -> str | None`; `_dedup.load_sidecar(path) -> dict`, `_dedup.save_sidecar(path, dict) -> None`, `_dedup.needs_upload(filename, mtime, sidecar) -> bool` (from Task 3.2).
- Produces: `async def upload_batch(self, files: list[str], hass=None, throttle: float = _UPLOAD_THROTTLE_SECONDS, sidecar_path: str | None = None) -> list[str]` — for each file, skips it when `sidecar_path` is given and `needs_upload()` is False (this is what makes a second run of an unchanged folder upload **0 files** — criterion 12); otherwise uploads with a `throttle`-second sleep **before** each actually-uploaded item after the first, records the returned content_id + mtime in the sidecar, and returns the list of content ids uploaded this run. Module constant `_UPLOAD_THROTTLE_SECONDS = 2.0`.

- [ ] **Step 1: Researcher lock-in** — record `upload()`'s real signature/line range in adopted `art.py` (8.3.3 ~L1720) and confirm it returns the new `content_id` string. Confirm `import asyncio` and `import os` are present at top and that `_dedup` (Tasks 3.1/3.2) is importable as `from . import _dedup` (or `import _dedup` in the test path).

- [ ] **Step 2: Write the failing test**

`tests/api/test_art_batch_throttle.py`:
```python
"""Batch throttle: ~2s between uploads; unchanged second run uploads 0 files."""
import asyncio
import os


async def test_batch_sleeps_two_seconds_between_uploads(art_client, monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(secs):
        sleeps.append(secs)

    uploaded: list[str] = []

    async def fake_upload(file, *a, **k):
        uploaded.append(file)
        return f"CID-{file}"

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)

    files = [f"img{i}.jpg" for i in range(30)]  # >25, no sidecar -> all upload
    result = await art_client.upload_batch(files)

    assert len(uploaded) == 30
    assert result == [f"CID-img{i}.jpg" for i in range(30)]
    # 30 uploads -> 29 inter-upload throttle sleeps of 2.0s each.
    assert sleeps == [2.0] * 29


async def test_batch_no_sleep_for_single_item(art_client, monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(secs):
        sleeps.append(secs)

    async def fake_upload(file, *a, **k):
        return f"CID-{file}"

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)

    await art_client.upload_batch(["only.jpg"])
    assert sleeps == []


async def test_second_run_of_unchanged_folder_uploads_zero(art_client, tmp_path, monkeypatch):
    async def no_sleep(_secs):
        return None

    calls: list[str] = []

    async def fake_upload(file, *a, **k):
        calls.append(file)
        return "CID-" + os.path.basename(file)

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)

    f = tmp_path / "cat.jpg"
    f.write_bytes(b"not-a-real-jpeg")
    sidecar = str(tmp_path / "sidecar.json")

    first = await art_client.upload_batch([str(f)], sidecar_path=sidecar)
    assert first == ["CID-cat.jpg"]
    assert calls == [str(f)]  # uploaded once

    calls.clear()
    second = await art_client.upload_batch([str(f)], sidecar_path=sidecar)
    assert second == []       # unchanged -> skipped
    assert calls == []        # 0 uploads on run 2 (criterion 12)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_art_batch_throttle.py -v`
Expected: FAIL — `AttributeError: 'SamsungTVAsyncArt' object has no attribute 'upload_batch'`.

- [ ] **Step 4: Write minimal implementation** — add the constant + a dual-mode `_dedup` import near the top of `art.py` (works both as a package and as the bare module the tests import), ensure `import os` is present, and add the method to the class:

```python
_UPLOAD_THROTTLE_SECONDS = 2.0

try:
    from . import _dedup  # normal package import inside HA
except ImportError:  # test/standalone: conftest.py put the api dir on sys.path
    import _dedup
```
```python
    async def upload_batch(
        self,
        files: list[str],
        hass=None,
        throttle: float = _UPLOAD_THROTTLE_SECONDS,
        sidecar_path: str | None = None,
    ) -> list[str]:
        """Upload files with ~2s spacing; skip unchanged files via the sidecar.

        A second run of an unchanged folder uploads 0 files (criterion 12).
        """
        sidecar = _dedup.load_sidecar(sidecar_path) if sidecar_path else {}
        content_ids: list[str] = []
        did_upload = False
        for file in files:
            name = os.path.basename(file)
            mtime = os.path.getmtime(file) if os.path.exists(file) else 0.0
            if sidecar_path and not _dedup.needs_upload(name, mtime, sidecar):
                continue  # unchanged since last run -> skip
            if did_upload:
                await asyncio.sleep(throttle)
            cid = await self.upload(file, hass=hass)
            did_upload = True
            if cid:
                content_ids.append(cid)
                sidecar[name] = {"content_id": cid, "modified": mtime}
        if sidecar_path:
            _dedup.save_sidecar(sidecar_path, sidecar)
        return content_ids
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_art_batch_throttle.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/samsungtv_smart/api/art.py tests/api/test_art_batch_throttle.py
git commit -m "feat(art): batch upload throttle (~2s) + sidecar-aware skip

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 3.4: P3 deploy + TV-verify (serialized deploy lane)

**Files:**
- Create: `docs/reference/p3-verify-note.md`

**Interfaces:**
- Consumes: `p3-dedup-upload` branch; deploy script; a small known test image set on the TV.
- Produces: TV-verified proof of criteria 11, 12, 13, 15, 16. **TV-verify runs against both Frames: `media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`.**

- [ ] **Step 1: Full suite green + no pyc**

Run: `python -m pytest tests/ -v && echo "pyc:" && git ls-files '*/__pycache__/*.pyc' | wc -l`
Expected: all pass; `pyc: 0`.

- [ ] **Step 2: Take the deploy lane, merge, deploy**

Run:
```bash
git checkout frame-art-best-in-class
git merge --no-ff p3-dedup-upload -m "merge: P3 dedup + sidecar + throttle"
scripts/deploy_to_ark.sh
```
Expected: `>> no samsungtv errors in recent log`.

- [ ] **Step 3: TV-verify dedup + sidecar (criteria 11, 12)** — with a small known image folder: run the upload batch twice. Record the TV's art count after run 1 and run 2.
Expected: run 2 uploads **0 files**; art count unchanged; no `SAM-F####`/`MY-F####` item modified or deleted. A sidecar JSON exists on Ark alongside the config.

- [ ] **Step 4: TV-verify throttle (criterion 13)** — upload a batch of **> 25 images** end-to-end.
Expected: zero failures in the log; all content ids returned.

- [ ] **Step 5: Regression check (criterion 16)** — re-run Task 1.1/1.2 checks. Write `docs/reference/p3-verify-note.md` with per-criterion evidence and commit:
```bash
git add docs/reference/p3-verify-note.md
git commit -m "docs: P3 TV-verify note (criteria 11-13, 15, 16)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P3 GATE:** criteria 11, 12, 13, 15, 16 pass.

---

## P4 — WebSocket auto-reconnect / keepalive _(parallel-authored on `p4-reconnect`; isolated deploy slot)_

### Task 4.1: Backoff reconnect + keepalive ping in the receive loop

**Files:**
- Modify: `custom_components/samsungtv_smart/api/art.py` (`_receive_loop`, add `_backoff_delay`, keepalive)
- Test: `tests/api/test_art_reconnect.py`

**Interfaces:**
- Consumes: `SamsungTVAsyncArt.open() -> bool`, `self._connected: bool`, `self._ws`.
- Produces: `def _backoff_delay(attempt: int) -> float` (bounded exponential, capped at 60.0); reconnect wiring so a closed WS mid-session triggers `open()` again with backoff; a keepalive that pings on an idle interval. Constant `_KEEPALIVE_INTERVAL = 60.0`, `_MAX_BACKOFF = 60.0`.

- [ ] **Step 1: Researcher lock-in** — record the real line range of `_receive_loop()` (8.3.3 ~L533) and confirm it currently `break`s on `CLOSED`/`ERROR` and sets `self._connected = False` in `finally` with no reconnect. Confirm `open()`'s signature and that it starts `_recv_task`.

- [ ] **Step 2: Write the failing test**

`tests/api/test_art_reconnect.py`:
```python
"""Auto-reconnect: a closed WS mid-session must trigger a backed-off reconnect."""


def test_backoff_delay_grows_and_caps(art_client):
    import art
    assert art.SamsungTVAsyncArt._backoff_delay(0) == 1.0
    assert art.SamsungTVAsyncArt._backoff_delay(1) == 2.0
    assert art.SamsungTVAsyncArt._backoff_delay(2) == 4.0
    # capped at 60s no matter how high the attempt count
    assert art.SamsungTVAsyncArt._backoff_delay(20) == 60.0


async def test_receive_loop_reconnects_on_close(art_client, monkeypatch):
    reopened = {"count": 0}

    async def fake_open():
        reopened["count"] += 1
        art_client._connected = True
        return True

    async def no_sleep(_secs):
        return None

    import asyncio
    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(art_client, "open", fake_open)

    # Simulate: loop body observed a closed socket once, then we stop.
    art_client._connected = True
    await art_client._reconnect_with_backoff(max_attempts=1)

    assert reopened["count"] == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/api/test_art_reconnect.py -v`
Expected: FAIL — `AttributeError: ... has no attribute '_backoff_delay'` / `_reconnect_with_backoff`.

- [ ] **Step 4: Write minimal implementation** — add constants near the top of `art.py` and methods to the class:

```python
_KEEPALIVE_INTERVAL = 60.0
_MAX_BACKOFF = 60.0
```
```python
    @staticmethod
    def _backoff_delay(attempt: int) -> float:
        """Exponential backoff (1, 2, 4, ...) capped at _MAX_BACKOFF seconds."""
        return float(min(2 ** attempt, int(SamsungTVAsyncArt._MAX_BACKOFF)))

    async def _reconnect_with_backoff(self, max_attempts: int = 6) -> bool:
        """Try to reopen the WS with exponential backoff. True if reconnected."""
        for attempt in range(max_attempts):
            await asyncio.sleep(self._backoff_delay(attempt))
            if await self.open():
                _LOGGER.debug("Art API: reconnected after %d attempt(s)", attempt + 1)
                return True
        _LOGGER.warning("Art API: reconnect gave up after %d attempts", max_attempts)
        return False
```
Then, in `_receive_loop`, replace the plain `break`-and-exit on `CLOSED`/`ERROR` so that when the socket closes unexpectedly (not via `close()`), it schedules a reconnect. In the `finally` block, if `self._connected` was not intentionally torn down, kick off `asyncio.create_task(self._reconnect_with_backoff())`. Add a keepalive: in `open()`, after starting `_recv_task`, also start `self._keepalive_task = asyncio.create_task(self._keepalive())`:
```python
    async def _keepalive(self) -> None:
        """Emit a periodic ping so an idle Art WS session is not dropped."""
        try:
            while self._connected and self._ws and not self._ws.closed:
                await asyncio.sleep(self._KEEPALIVE_INTERVAL)
                if self._ws and not self._ws.closed:
                    await self._ws.ping()
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
```
(Cancel `_keepalive_task` in `close()` alongside `_recv_task`. Use the logger name the researcher locked in at Step 1 — `_LOGGER` or `self._log`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/api/test_art_reconnect.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/samsungtv_smart/api/art.py tests/api/test_art_reconnect.py
git commit -m "feat(art): WS auto-reconnect (bounded backoff) + idle keepalive ping

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 4.2: P4 deploy + TV-verify (ISOLATED deploy slot — do not co-deploy with another risky branch)

**Files:**
- Create: `docs/reference/p4-verify-note.md`

**Interfaces:**
- Consumes: `p4-reconnect` branch; deploy script; the Reboot-TV button as manual recovery fallback.
- Produces: TV-verified proof of criterion 14 (+ 15, 16). **TV-verify runs against both Frames: `media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`.**

- [ ] **Step 1: Full suite green + no pyc**

Run: `python -m pytest tests/ -v && git ls-files '*/__pycache__/*.pyc' | wc -l`
Expected: all pass; `0`.

- [ ] **Step 2: Take an ISOLATED deploy slot, merge, deploy**

Run:
```bash
git checkout frame-art-best-in-class
git merge --no-ff p4-reconnect -m "merge: P4 WS auto-reconnect + keepalive"
scripts/deploy_to_ark.sh
```
Expected: `>> no samsungtv errors in recent log`. (No other branch shares this deploy — a reconnect bug can wedge the live WS.)

- [ ] **Step 3: TV-verify recovery < 60 s (criterion 14)** — force a disconnect: press the Reboot-TV button (or drop the Art WS). Start a stopwatch.
Expected: the Art connection auto-recovers within **60 s** with **no HA restart** (art commands work again; log shows a reconnect line, no hot-loop). If it wedges, restore via `backup/live-install-B` (runbook) and iterate.

- [ ] **Step 4: TV-verify idle keepalive ≥ 10 min (criterion 14)** — leave the session idle for ≥ 10 min, then issue an art command.
Expected: the command succeeds without a fresh connect (keepalive kept it alive).

- [ ] **Step 5: Regression check (criterion 16), write note, commit**

Re-run Task 1.1/1.2 checks. Create `docs/reference/p4-verify-note.md`, then:
```bash
git add docs/reference/p4-verify-note.md
git commit -m "docs: P4 TV-verify note (criterion 14 recovery + keepalive, 15, 16)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P4 GATE:** criterion 14 passes; 15, 16 hold.

---

## P5 — Gallery / browse UX _(core; parallel-authored on `p5-gallery`)_

### Task 5.1: Expose the art library as a `media_source`

**Files:**
- Create: `custom_components/samsungtv_smart/media_source.py`
- Modify: `custom_components/samsungtv_smart/manifest.json` (add `media_source` to `dependencies`)
- Test: `tests/test_media_source.py`

**Interfaces:**
- Consumes: HA `homeassistant.components.media_source` (`MediaSource`, `BrowseMediaSource`, `MediaSourceItem`, `PlayMedia`); C's thumbnail view `/api/samsungtv_smart/thumbnail?path=<content_id>&w=<w>`; the art client's `available(category) -> list`.
- Produces: `class SamsungArtMediaSource(MediaSource)` with `async_browse_media(item) -> BrowseMediaSource` (children = the TV's art, each `thumbnail=` the HTTP view URL, no base64) and `async_resolve_media(item) -> PlayMedia`. **2026 change: `BrowseMediaSource(domain=...)` is mandatory** — pass `domain=DOMAIN`. `async def async_get_media_source(hass) -> SamsungArtMediaSource`.

- [ ] **Step 1: Researcher lock-in** — open the adopted `__init__.py`/`const.py`; record `DOMAIN`, the entry-id key in `hass.data[DOMAIN]`, and how to reach the art client + the thumbnail view path. Confirm the adopted base does NOT already ship a `media_source.py`.

- [ ] **Step 2: Write the failing test**

`tests/test_media_source.py`:
```python
"""media_source: browse the art library as a thumbnail grid (no base64)."""
import sys
from pathlib import Path

COMP = Path(__file__).resolve().parents[1] / "custom_components" / "samsungtv_smart"
sys.path.insert(0, str(COMP))


def test_thumbnail_url_builder_uses_http_view():
    import media_source as ms
    url = ms.thumbnail_url("MY-F0001", width=200)
    assert url == "/api/samsungtv_smart/thumbnail?path=MY-F0001&w=200"
    assert "base64" not in url


def test_browse_child_carries_thumbnail_and_domain():
    import media_source as ms
    child = ms.build_art_child(content_id="MY-F0001", title="Sunset")
    assert child.domain == ms.DOMAIN
    assert child.thumbnail == "/api/samsungtv_smart/thumbnail?path=MY-F0001&w=200"
    assert child.can_play is True
    assert child.can_expand is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_media_source.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'media_source'` (or `homeassistant` import error → install HA in the test env: `pip install homeassistant`).

- [ ] **Step 4: Write minimal implementation** — `media_source.py` with the pure helpers the test pins plus the MediaSource class:

```python
"""Expose the Frame TV art library as a browsable media_source grid."""
from __future__ import annotations

from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN


def thumbnail_url(content_id: str, width: int = 200) -> str:
    """Build the HTTP-view thumbnail URL (no base64)."""
    return f"/api/samsungtv_smart/thumbnail?path={content_id}&w={width}"


def build_art_child(content_id: str, title: str) -> BrowseMediaSource:
    """One browsable, playable art item with an HTTP-view thumbnail."""
    return BrowseMediaSource(
        domain=DOMAIN,  # 2026: mandatory
        identifier=content_id,
        media_class=MediaClass.IMAGE,
        media_content_type=MediaType.IMAGE,
        title=title,
        can_play=True,
        can_expand=False,
        thumbnail=thumbnail_url(content_id, 200),
    )


class SamsungArtMediaSource(MediaSource):
    """Browse the Frame's art library."""

    name = "Samsung Frame Art"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        art = _get_art_client(self.hass)
        children = [
            build_art_child(v["content_id"], v.get("content_id", ""))
            for v in (await art.available("MY-C0002") or [])
        ]
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.IMAGE,
            title="Samsung Frame Art",
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        return PlayMedia(thumbnail_url(item.identifier, 1920), "image/jpeg")


def _get_art_client(hass: HomeAssistant):
    entry = next(iter(hass.data[DOMAIN].values()))
    return entry.art  # confirm the real attribute at Step 1 lock-in


async def async_get_media_source(hass: HomeAssistant) -> SamsungArtMediaSource:
    return SamsungArtMediaSource(hass)
```
Add `"media_source"` to `manifest.json` `dependencies`. (Adjust `_get_art_client` to the real accessor recorded at Step 1.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_media_source.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add custom_components/samsungtv_smart/media_source.py custom_components/samsungtv_smart/manifest.json tests/test_media_source.py
git commit -m "feat: browsable art library via media_source (HTTP-view thumbnails)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 5.2: Ship `camera-gallery-card` + a ready-to-paste Lovelace example

**Files:**
- Create: `docs/gallery/camera-gallery-card-example.yaml`
- Create: `docs/gallery/README.md`

**Interfaces:**
- Consumes: the `media_source` from Task 5.1; `TheScubaDiver/camera-gallery-card` (87★, MIT, media_source-driven, visual editor).
- Produces: a working Lovelace card config wired to `media-source://samsungtv_smart` and to `media_player.living_room_tv` for pick-to-select.

- [ ] **Step 1: Researcher lock-in** — confirm the media_source identifier prefix HA assigns (`media-source://<DOMAIN>`), and record the art-select entity id from Task 1.1 for the pick action.

- [ ] **Step 2: Write the Lovelace example**

`docs/gallery/camera-gallery-card-example.yaml`:
```yaml
# Requires TheScubaDiver/camera-gallery-card (MIT) installed via HACS.
type: custom:camera-gallery-card
title: Frame Art
media_source: media-source://samsungtv_smart
columns: 4
# Picking a thumbnail selects it on the Frame within 10s:
tap_action:
  action: call-service
  service: select.select_option
  target:
    entity_id: select.living_room_tv_art   # confirm exact id from Task 1.1
  data:
    option: "{{ media_content_id }}"
```

- [ ] **Step 3: Write the install/usage README**

`docs/gallery/README.md`: install `camera-gallery-card` via HACS custom repo `https://github.com/TheScubaDiver/camera-gallery-card` (MIT), then paste the example into a dashboard; note it replaces the older `folder-gallery-card`; images are served by the thumbnail HTTP view (no base64).

- [ ] **Step 4: Commit**

```bash
git add docs/gallery/
git commit -m "docs(gallery): camera-gallery-card Lovelace example wired to the Frame

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 5.3: P5 deploy + TV-verify (serialized deploy lane)

**Files:**
- Create: `docs/reference/p5-verify-note.md`

**Interfaces:**
- Consumes: `p5-gallery` branch; deploy script; a HA dashboard with the card.
- Produces: TV-verified proof of criterion 17 (+ 15, 16). **TV-verify runs against both Frames: `media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`.**

- [ ] **Step 1: Full suite green + no pyc**

Run: `python -m pytest tests/ -v && git ls-files '*/__pycache__/*.pyc' | wc -l`
Expected: all pass; `0`.

- [ ] **Step 2: Take the deploy lane, merge, deploy**

Run:
```bash
git checkout frame-art-best-in-class
git merge --no-ff p5-gallery -m "merge: P5 gallery media_source + card"
scripts/deploy_to_ark.sh
```
Expected: `>> no samsungtv errors in recent log`.

- [ ] **Step 3: TV-verify gallery browse + pick (criterion 17)** — add the card to a dashboard; confirm the art library renders as a thumbnail grid (images from the HTTP view, no base64), then pick an image.
Expected: the grid populates; picking selects it on `media_player.living_room_tv` within **10 s**.

- [ ] **Step 4: Regression check (criterion 16), write note, commit**

Re-run Task 1.1/1.2 checks. Create `docs/reference/p5-verify-note.md`, then:
```bash
git add docs/reference/p5-verify-note.md
git commit -m "docs: P5 TV-verify note (criterion 17 gallery browse+pick, 15, 16)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P5 GATE:** criterion 17 passes; 15, 16 hold.

---

## P6 — Presence-aware auto-art blueprint _(core; after P2 bug 1, `p6-blueprint`)_

### Task 6.1: Author the presence-aware `KEY_RIGHT` auto-art blueprint

**Files:**
- Create: `blueprints/automation/samsungtv_smart/frame_auto_art.yaml`
- Test: `tests/test_blueprint_frame_auto_art.py`

**Interfaces:**
- Consumes: `in_artmode()` behavior via the media_player art services (P2 bug 1 landed); an occupancy/motion `binary_sensor`; the Frame `media_player`.
- Produces: an importable HA blueprint that (a) rotates art on a schedule via native `KEY_RIGHT`, and (b) only re-asserts art mode when the presence sensor reports `on`. Inputs: `frame_target` (media_player), `presence_sensor` (binary_sensor), `rotate_interval` (duration).

- [ ] **Step 1: Researcher lock-in** — record the exact `remote`/`media_player` service the adopted integration exposes to send `KEY_RIGHT` (e.g. `samsungtv_smart.send_key` or `media_player` remote), and the art-mode assert service/attribute. Confirm the Frame media_player entity id.

- [ ] **Step 2: Write the failing test (blueprint is valid YAML with required schema)**

`tests/test_blueprint_frame_auto_art.py`:
```python
"""The auto-art blueprint must be valid YAML with the required blueprint schema."""
from pathlib import Path

import yaml

BP = Path(__file__).resolve().parents[1] / "blueprints" / "automation" / "samsungtv_smart" / "frame_auto_art.yaml"


def test_blueprint_parses_and_has_schema():
    doc = yaml.safe_load(BP.read_text())
    assert "blueprint" in doc
    bp = doc["blueprint"]
    assert bp["domain"] == "automation"
    inputs = bp["input"]
    assert {"frame_target", "presence_sensor", "rotate_interval"} <= set(inputs)


def test_blueprint_gates_on_presence():
    text = BP.read_text()
    # Recovery must be guarded by the presence sensor input.
    assert "presence_sensor" in text
    assert "KEY_RIGHT" in text
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_blueprint_frame_auto_art.py -v`
Expected: FAIL — `FileNotFoundError` (blueprint not yet created).

- [ ] **Step 4: Write minimal implementation**

`blueprints/automation/samsungtv_smart/frame_auto_art.yaml`:
```yaml
blueprint:
  name: Samsung Frame Auto-Art (presence-aware)
  description: >
    Rotates Frame TV art on a schedule via native KEY_RIGHT, and re-asserts
    art mode only when the room is occupied. Requires the samsungtv_smart
    integration with the in_artmode() bug-1 fix.
  domain: automation
  input:
    frame_target:
      name: Frame TV media_player
      selector:
        entity:
          domain: media_player
    presence_sensor:
      name: Room presence / motion sensor
      selector:
        entity:
          domain: binary_sensor
    rotate_interval:
      name: Rotate interval
      default: "01:00:00"
      selector:
        duration: {}
trigger:
  - platform: time_pattern
    hours: "/1"
condition:
  - condition: state
    entity_id: !input presence_sensor
    state: "on"
action:
  - service: samsungtv_smart.send_key   # confirm exact service at Step 1 lock-in
    target:
      entity_id: !input frame_target
    data:
      key: KEY_RIGHT
mode: single
```
(Replace `samsungtv_smart.send_key` / trigger interval wiring with the exact service and the `rotate_interval` input mechanism recorded at Step 1.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_blueprint_frame_auto_art.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add blueprints/automation/samsungtv_smart/frame_auto_art.yaml tests/test_blueprint_frame_auto_art.py
git commit -m "feat(blueprint): presence-aware KEY_RIGHT auto-art rotation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 6.2: P6 deploy/import + TV-verify

**Files:**
- Create: `docs/reference/p6-verify-note.md`

**Interfaces:**
- Consumes: `p6-blueprint` branch; deploy script; a real presence sensor.
- Produces: TV-verified proof of criterion 18. **TV-verify runs against both Frames as separate per-TV automation instances: `media_player.living_room_tv` + `media_player.kitchen_smartthings_hub`.**

- [ ] **Step 1: Suite green + merge + deploy**

Run:
```bash
python -m pytest tests/ -v
git checkout frame-art-best-in-class
git merge --no-ff p6-blueprint -m "merge: P6 auto-art blueprint"
scripts/deploy_to_ark.sh
```
Expected: all pass; `>> no samsungtv errors in recent log`.

- [ ] **Step 2: Import the blueprint cleanly (criterion 18)** — in HA → Settings → Automations → Blueprints → Import, point at the blueprint file (or its raw GitHub URL).
Expected: imports with no schema errors; the three inputs render.

- [ ] **Step 3: TV-verify rotation + presence gating (criterion 18)** — create an automation from the blueprint wired to `media_player.living_room_tv` and a real motion sensor. Trigger a rotation with presence `on`; then set presence `off` and confirm no re-assert.
Expected: art rotates on schedule when occupied; art mode is only re-asserted when presence is detected.

- [ ] **Step 4: Write note + commit**

Create `docs/reference/p6-verify-note.md`, then:
```bash
git add docs/reference/p6-verify-note.md
git commit -m "docs: P6 TV-verify note (criterion 18 blueprint import + rotation)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P6 GATE:** criterion 18 passes.

---

## P7 — Contribute-back PRs _(core; each follows its TV-verified source phase)_

> **Before any PR:** read `TheFab21/ha-samsungtv-smart`'s contributing/PR template if present, search open AND closed PRs for duplicates, and disclose this is agent-generated (model, harness). Merge by TheFab21 is NOT required — our fork stays the deployed artifact. Do NOT bundle unrelated changes; one problem per PR.

### Task 7.1: PR — firmware-compat fixes (P2)

**Files:**
- Modify: `docs/reference/contribute-back-prs.md` (create; record PR link)

**Interfaces:**
- Consumes: the TV-verified P2 commits (bugs 1–4) + their regression tests.
- Produces: a focused public PR to `TheFab21/ha-samsungtv-smart` for the firmware fixes; link recorded. Satisfies criterion 19 (part 1).

- [ ] **Step 1: Confirm P2 is TV-verified** — check `docs/reference/p2-verify-note.md` shows criteria 7–10 green. Do not open the PR otherwise.

- [ ] **Step 2: Search for duplicate PRs upstream**

Run:
```bash
gh pr list --repo TheFab21/ha-samsungtv-smart --state all --search "artmode matte upload" --limit 30
```
Expected: review results; if a duplicate exists, STOP and record it in the doc instead of opening a new one.

- [ ] **Step 3: Create a focused branch off the fab21 tag with only the four fixes + tests**

Run:
```bash
git checkout -b pr/firmware-compat-fixes 8.3.3
git checkout frame-art-best-in-class -- \
  custom_components/samsungtv_smart/api/art.py \
  tests/api/test_art_bug1_artmode_detection.py \
  tests/api/test_art_bug2_matte_list.py \
  tests/api/test_art_bug3_artmode_field.py \
  tests/api/test_art_bug4_upload_type.py
python -m pytest tests/api/test_art_bug1_artmode_detection.py tests/api/test_art_bug2_matte_list.py tests/api/test_art_bug3_artmode_field.py tests/api/test_art_bug4_upload_type.py -v
```
Expected: the four bug test files pass on top of the clean tag. (If `art.py` also carries P3/P4 changes, cherry-pick only the bug-fix hunks so the PR is firmware-fixes-only.)

- [ ] **Step 4: Open the PR and record the link**

Run:
```bash
git push origin pr/firmware-compat-fixes
gh pr create --repo TheFab21/ha-samsungtv-smart --base master --head chansearrington:pr/firmware-compat-fixes \
  --title "Fix 2025-firmware art-mode/matte/status/upload-type compatibility" \
  --body "Four small firmware-compat fixes with regression tests: (1) in_artmode() trusts art-WS get_artmode_status over REST PowerState=standby; (2) get_matte_list reads matte_list or matte_type_list; (3) get_artmode reads value or status; (4) upload detects real type via PIL and sends jpg. Agent-generated (Claude Opus 4.8, Claude Code); no coordination assumed. Each fix has a reproduce-then-fix test."
```
Record the returned URL in `docs/reference/contribute-back-prs.md`.

- [ ] **Step 5: Commit the record**

```bash
git checkout frame-art-best-in-class
git add docs/reference/contribute-back-prs.md
git commit -m "docs: record contribute-back PR for firmware-compat fixes

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 7.2: PR — dedup / upload (P3)

**Files:**
- Modify: `docs/reference/contribute-back-prs.md` (append PR link)

**Interfaces:**
- Consumes: TV-verified P3 commits (`_dedup.py`, sidecar, throttle) + tests.
- Produces: a focused public PR for dedup/upload; link recorded. Satisfies criterion 19 (part 2).

- [ ] **Step 1: Confirm P3 is TV-verified** — `docs/reference/p3-verify-note.md` shows criteria 11–13 green. Search duplicates:
```bash
gh pr list --repo TheFab21/ha-samsungtv-smart --state all --search "dedup upload throttle" --limit 30
```
Expected: no duplicate; else STOP and record.

- [ ] **Step 2: Create a focused branch with `_dedup.py` + throttle + tests**

Run:
```bash
git checkout -b pr/dedup-upload 8.3.3
git checkout frame-art-best-in-class -- \
  custom_components/samsungtv_smart/api/_dedup.py \
  tests/api/test_dedup_perceptual.py \
  tests/api/test_dedup_sidecar.py \
  tests/api/test_art_batch_throttle.py
# also cherry-pick the upload_batch hunk in art.py
python -m pytest tests/api/test_dedup_perceptual.py tests/api/test_dedup_sidecar.py -v
```
Expected: dedup tests pass on the clean tag.

- [ ] **Step 3: Open the PR and record the link**

Run:
```bash
git push origin pr/dedup-upload
gh pr create --repo TheFab21/ha-samsungtv-smart --base master --head chansearrington:pr/dedup-upload \
  --title "Perceptual dedup + content_id sidecar map + batch upload throttle" \
  --body "Adds perceptual dedup (grayscale->384x216->GaussianBlur(2)->diff<=1.0) so TV re-encodes don't cause re-uploads; a content_id sidecar map that skips unchanged files and never touches SAM-F####/MY-F#### art; and a ~2s batch throttle (batches >25 fail without it). Unit tests included. Agent-generated (Claude Opus 4.8, Claude Code); no coordination assumed."
```
Append the URL to `docs/reference/contribute-back-prs.md`.

- [ ] **Step 4: Commit the record**

```bash
git checkout frame-art-best-in-class
git add docs/reference/contribute-back-prs.md
git commit -m "docs: record contribute-back PR for dedup/upload

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

### Task 7.3: PR — WebSocket auto-reconnect (P4)

**Files:**
- Modify: `docs/reference/contribute-back-prs.md` (append PR link)

**Interfaces:**
- Consumes: TV-verified P4 commits (reconnect/keepalive) + tests.
- Produces: a focused public PR for reconnect; link recorded. Satisfies criterion 19 (part 3, completes it).

- [ ] **Step 1: Confirm P4 is TV-verified** — `docs/reference/p4-verify-note.md` shows criterion 14 green. Search duplicates:
```bash
gh pr list --repo TheFab21/ha-samsungtv-smart --state all --search "reconnect keepalive websocket" --limit 30
```
Expected: no duplicate; else STOP and record.

- [ ] **Step 2: Create a focused branch with the reconnect hunk + test**

Run:
```bash
git checkout -b pr/ws-reconnect 8.3.3
git checkout frame-art-best-in-class -- tests/api/test_art_reconnect.py
# cherry-pick only the reconnect/keepalive/_backoff_delay hunks in art.py
python -m pytest tests/api/test_art_reconnect.py -v
```
Expected: reconnect tests pass on the clean tag.

- [ ] **Step 3: Open the PR and record the link**

Run:
```bash
git push origin pr/ws-reconnect
gh pr create --repo TheFab21/ha-samsungtv-smart --base master --head chansearrington:pr/ws-reconnect \
  --title "Art WebSocket auto-reconnect (bounded backoff) + idle keepalive" \
  --body "The Art WS receive loop currently exits on close and open() is lazy, so a dropped WS silently dies until a HA restart. Adds bounded exponential backoff reconnect (capped 60s) and an idle keepalive ping. Recovery verified <60s on a real 2025 Frame; idle session survives >10min. Test included. Agent-generated (Claude Opus 4.8, Claude Code); no coordination assumed."
```
Append the URL to `docs/reference/contribute-back-prs.md`.

- [ ] **Step 4: Commit the record**

```bash
git checkout frame-art-best-in-class
git add docs/reference/contribute-back-prs.md
git commit -m "docs: record contribute-back PR for WS auto-reconnect

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

**P7 GATE:** criterion 19 passes (one PR per proven improvement opened upstream with tests; links recorded).

---

## Success-criteria → task map (all 19 covered)

| # | Criterion | Task(s) |
|---|---|---|
| 1 | Base adopted cleanly | 0.1, 0.4 |
| 2 | Deploy path works (zero-error load) | 0.6 (step 2) |
| 3 | Backup-before-deploy proven | 0.2 |
| 4 | Smoke test (TV present/controllable) | 0.6 (step 3) |
| 5 | Art dropdown populated + selection ≤10s | 1.1 |
| 6 | C's platforms present | 1.2 |
| 7 | Bug 1 art-mode detection | 2.1, 2.5 |
| 8 | Bug 2 matte list | 2.2, 2.5 |
| 9 | Bug 3 art-status field | 2.3, 2.5 |
| 10 | Bug 4 upload type | 2.4, 2.5 |
| 11 | Dedup works | 3.1, 3.4 |
| 12 | Sidecar map works | 3.2, 3.4 |
| 13 | Batch throttle | 3.3, 3.4 |
| 14 | Auto-reconnect / keepalive | 4.1, 4.2 |
| 15 | Tests green, no pyc | 0.3, and re-checked in 2.5/3.4/4.2/5.3/6.2 |
| 16 | No regressions of 4–6 | 2.5, 3.4, 4.2, 5.3, 6.2 (regression step) |
| 17 | Gallery browsing | 5.1, 5.2, 5.3 |
| 18 | Auto-art blueprint | 6.1, 6.2 |
| 19 | Contribute-back PRs | 7.1, 7.2, 7.3 |

Total: **28 tasks** — P0: 6, P1: 3, P2: 5, P3: 4, P4: 2, P5: 3, P6: 2, P7: 3.
