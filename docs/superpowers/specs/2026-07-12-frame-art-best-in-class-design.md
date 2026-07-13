# Frame TV "Best-in-Class Art Mode" — Design Specification

_Written 2026-07-12. Feeds the writing-plans step next. Source of truth for findings and the
already-settled decisions: `../../reference/frame-art-research.md` (the "digest"). This spec does
not re-litigate anything the digest marks as decided — it turns those decisions into a buildable,
verifiable plan._

**Reading guide for Chanse (non-technical):** every section opens in plain English. Anything that
needs code-level detail is fenced under a **`[Technical detail]`** heading you can skip. You have
**two** Samsung Frame TVs, and **both are first-class verification targets** — every "verified on
the real Frame TV" claim must hold on **each** of them: the living-room Frame
(`media_player.living_room_tv`, host `192.168.1.64`) AND the kitchen Frame
(`media_player.kitchen_smartthings_hub` — note the naming quirk — host `192.168.1.140`). Both are
65" model QN65LS03BAFXZA, each its own config entry, both running on the Ark server. When you see a
`media_player.living_room_tv` reference below, read it as shorthand for "each Frame".

---

## 1. Goal & context

**Plain English.** We want your Samsung Frame TV's "Art Mode" to work better than any other
Home Assistant setup out there — art you can browse and pick from a dropdown, art that reliably
uploads and switches, and a connection to the TV that heals itself instead of silently dying. To
get there fast, we stop maintaining our own hand-grown version and adopt the strongest existing
version as our new starting point, then layer on the handful of genuinely original improvements
that nobody else has built.

**Lineage / decision summary (settled — see digest §1–5).** There is a single fork family for
this integration. Our old fork ("A", `chansearrington/ha-samsungtv-smart`, manifest 6.3.2) has
**nothing functional** that the leading fork lacks. The leading fork is **TheFab21's**
(`TheFab21/ha-samsungtv-smart`, "C", Apache-2.0, master manifest 8.3.3, release tags up to 8.24,
last push 2026-07-10). C is a **strict superset** of our fork — in fact our art code was
originally written by TheFab21. C's history is detached from ours (GitHub can't merge it via PR),
so we adopt it by **tree-level replacement** of `custom_components/samsungtv_smart/` plus shared
assets. Confirmed decisions:

- Adopt **C at its latest tag** (pin the exact latest tag at execution time; master is 8.3.3,
  tags go to 8.24) as our new base, by tree-level copy.
- Keep it as **our own deployable fork**, tracking `fab21` as an upstream remote for future
  syncs. The deployed artifact stays ours.
- We have **no relationship** with TheFab21 → contribute our improvements back as **best-effort
  public PRs only**; assume no coordination and that they may never merge.
- Do **not** rebuild entities C already ships. Do **not** add image resizing before upload.
- Our **genuine value-add** (nobody has these): firmware-compatibility bug fixes, image dedup +
  content_id sidecar map, upload type detection, batch upload throttle, and WebSocket
  auto-reconnect/keepalive (digest §5).
- Verify everything against the **real Frame TVs** on Ark — **both Frames** (living room
  `media_player.living_room_tv` @ `192.168.1.64` AND kitchen `media_player.kitchen_smartthings_hub`
  @ `192.168.1.140`; both model QN65LS03BAFXZA, each its own config entry) — via `ssh ark`; HA
  docker container `homeassistant`; config `/mnt/user/appdata/homeassistant`.

This is a **Claude Code agent-team-driven** effort: a coordinator plus specialist agents run each
phase in a loop until acceptance criteria pass, visible in Herdr/Moshi (§6).

---

## 2. Success criteria

Numbered, concrete, and verifiable. Unless noted, "verified" means observed on **each Frame** (the
living-room `media_player.living_room_tv` **AND** the kitchen `media_player.kitchen_smartthings_hub`)
via HA service calls and entity-state inspection — a criterion is only met when it holds on **both**
Frames. Each phase (§5) gates on the subset that applies to it.

**Foundation**
1. **Base adopted cleanly.** `custom_components/samsungtv_smart/` on our fork is byte-equivalent
   to C's chosen latest tag (aside from our intentionally re-applied files), C's `LICENSE`/`NOTICE`
   and per-file SPDX headers are retained, and the pinned tag is recorded in this repo.
2. **Deploy path works.** A single documented command rsyncs the component to Ark and restarts the
   `homeassistant` container; after restart the integration loads with **zero errors** in the HA
   log (only HA's standard "custom integration" notice; the known cosmetic "SmartThings report TV
   is off but status detected is on" warning is allowed — digest §8).
3. **Backup-before-deploy proven.** Before the first redeploy, the live install (B) is captured to
   a dedicated git branch, and restoring from that branch is shown to work.
4. **Smoke test passes.** After deploy, **each Frame** (living room `media_player.living_room_tv`
   AND kitchen `media_player.kitchen_smartthings_hub`) is present and controllable (power/basic
   media_player commands succeed), matching pre-deploy behavior.

**Baseline (C's shipped features, verified live)**
5. **Art dropdown populated.** The art-selection entity lists **≥ 10 artworks** from the TV, and
   selecting one **changes the displayed art on the TV within 10 s** (observed on the physical
   panel or via `get_artmode`/current-art state).
6. **C's platforms present.** The 11 selects, 5 numbers, Reboot-TV button, thumbnail HTTP view,
   and token-notify all instantiate for the Frame without error (digest §4).

**Firmware-compat fixes (digest §5, bugs 1–4) — each needs a regression test**
7. **Art-mode detection fixed (bug 1).** With the TV in Art Mode, the integration reports
   in-art-mode **true** even when REST `PowerState="standby"`; a regression test reproduces the
   old false-negative and passes on the fix.
8. **Matte list populated (bug 2).** The matte-type select is non-empty on the real TV; a
   regression test covers both `matte_type_list` and `matte_list` field names.
9. **Art-status field rename handled (bug 3).** `get_artmode()` returns correct on/off when the
   payload uses `status` (API 5.x) as well as `value`; regression test covers both.
10. **Upload type detection correct (bug 4).** Uploading a JPEG, a PNG, and an MPO each detect the
    real format via PIL and send the correct wire type (`jpg`, not `jpeg`); regression test covers
    all three plus a wrong caller hint.

**Differentiator features**
11. **Dedup works.** Re-uploading an already-present image does **not** create a duplicate on the
    TV (perceptual match: grayscale → resize 384×216 → GaussianBlur(2) → diff ≤ 1.0). Verified by
    running the same batch twice and confirming the TV's art count is unchanged on the second run.
12. **Sidecar map works.** A `content_id ↔ source-file` sidecar JSON exists; a second run of an
    unchanged folder uploads **0 files**; Samsung-Store (`SAM-F####`) and other tools' art
    (`MY-F####`) are never modified or deleted.
13. **Batch throttle holds.** A batch of **> 25 images** uploads with no failures (≈2 s spacing),
    verified end-to-end against the TV.
14. **Auto-reconnect works.** Killing the Art WebSocket mid-session (or a TV reboot) auto-recovers
    the connection **within 60 s** without a HA restart, with keepalive pings keeping an idle
    session alive for **≥ 10 min**; a test forces a disconnect and asserts recovery.

**UX & contribution (now core scope — user promoted from stretch)**
17. **Gallery browsing works.** The art library is browsable as a thumbnail grid on the HA
    dashboard (via `media_source` + `camera-gallery-card`), and picking an image selects it on
    **each Frame** (living room `media_player.living_room_tv` AND kitchen
    `media_player.kitchen_smartthings_hub`) within 10 s. Grid images are served by the thumbnail
    HTTP view (no base64).
18. **Auto-art blueprint works.** An installable HA blueprint imports cleanly, rotates art on the
    real Frame on schedule, and only re-asserts art mode when a presence/motion sensor reports the
    room occupied.
19. **Contribute-back PRs opened.** A focused, test-carrying public PR is opened to
    `TheFab21/ha-samsungtv-smart` for each proven improvement (firmware fixes, dedup/upload,
    reconnect); PR links are recorded in the repo. (Merge by TheFab21 is **not** required.)

**Quality gates (all phases)**
15. **Tests green.** All new/changed unit + regression tests pass in CI/local run; no committed
    `.pyc`/`__pycache__` (digest §8 — the 17 committed pyc files are removed and gitignored).
16. **No regressions.** Criteria 4–6 still pass after every later phase's deploy.

---

## 3. Non-goals / YAGNI

Explicitly **out of scope** — do not build these, do not let scope creep pull them in:

- **No pre-upload image resizing.** No 16:9 / 3840×2160 conversion. Raw bytes upload is correct;
  the TV + matte handle fitting. The *only* PIL resize permitted is the 384×216 dedup thumbnail
  (digest §5, "Explicitly do NOT do").
- **No rebuilding C's entities.** We do not re-implement selects/numbers/buttons/image/thumbnail/
  token-notify/media_player — C ships them and they work. The `janstrm` MIT repo is reference only.
- **No dependence on TheFab21 merging our PRs.** Contribute-back is best-effort and asynchronous;
  our fork is always the deployed artifact and must stand alone.
- **No public HACS release in this scope.** HACS custom-repo install is a later nicety. We
  *structure* the repo so it's HACS-ready (clean tree, no pyc, valid manifest) but shipping it is
  out of scope here.
- **No pre-upload crop/reframe *editor* UX.** We do not build an in-HA image-cropping/preview
  editor. (The `media_source` browse grid + `camera-gallery-card` and the auto-art blueprint ARE
  now in core scope — P5/P6 — but a crop editor is not.)
- **No SmartThings/OAuth rearchitecture.** We may re-apply our two doc files (`README_CORRECTIONS.md`,
  `README_OAUTH2.md`) but we don't touch that subsystem's behavior.

---

## 4. Architecture / components

**Plain English.** The integration is a set of Python files that HA loads. After adoption, the
whole folder is TheFab21's code. Our work touches a **small, well-contained set** of those files —
mostly one file, `api/art.py`, which is the piece that actually talks to the TV's Art service.
Everything else we mostly leave alone.

### Adopted module map (from C — digest §4)

| File | Role |
|---|---|
| `api/art.py` | Vendored async Art-service client (WebSocket). **Where almost all our changes land.** SPDX `LGPL-3.0`. |
| `api/ipcontrol.py` | Samsung JSON-RPC IP-control channel (port 1516); survives reboots; independent of the Art WebSocket. |
| `select.py` (~1717 lines) | 11 selects (Color Tone, Speaker Output, SmartThings Media Output, Matte Type, Matte Color, Picture Mode, Art Motion Sensitivity, Art Motion Timer, Art Brightness Sensor, …). |
| `number.py` (~806) | 5 numbers (IP Backlight 0–50, IP Picture, Art Brightness 0–100, Art Color Temperature −5..+5). |
| `button.py` (~141) | Reboot-TV over IP control (recovers a hung Art WebSocket). |
| `http_thumbnail.py` (~140) | On-demand resized-thumbnail HTTP view `/api/samsungtv_smart/thumbnail?path=…&w=…`, disk-cached JPEG q78, path-traversal guarded. Registered in `__init__.py` (~L1060). This is **how C serves art previews** — via an HTTP view + the gallery card, **not** an HA `ImageEntity`. Replaces base64-in-attribute bloat. |
| `token_notify.py` (~134) | Self-clearing FR/EN notifications for bad WS / IP-control tokens. |
| `media_player.py` (~4538) | Core entity; sophisticated power-state logic; already strips base64 from `frame_art_last_result` and skips existing downloads (the French "corrections" are already here). |
| `entity.py` | `SamsungTVEntity` base mixin all platforms extend. |
| `__init__.py` | Platform forwarding (`SAMSMART_PLATFORM`), `hass.data[DOMAIN][entry_id]`, thumbnail view registration, unload handling. |
| Shared assets | `folder-gallery-card.js`, `Frame_Art.md`, `SmartThings_API_Usage.md`, `IP_Control_Protocol_Reference.md`, `LICENSE`, `NOTICE`. |

### Where OUR changes land

Concentrated, by design, to keep future `fab21` syncs cheap:

- **`api/art.py`** — the four firmware-compat fixes (§5/§2 bugs 1–4), dedup + perceptual match,
  content_id sidecar map, upload type detection, batch throttle, and WebSocket
  reconnect/keepalive. This is the bulk of the work.
- **New small helper module(s) alongside `art.py`** *only if* a change is too large to sit
  cleanly inline (e.g. a `_dedup.py` for the perceptual-hash + sidecar logic). Keep the public
  surface of `art.py` stable so C's callers (`media_player.py`, platforms) need no edits.
- **Re-applied docs:** `README_CORRECTIONS.md`, `README_OAUTH2.md` (optional, digest §3).
- **Repo hygiene:** remove committed `__pycache__/*.pyc`, add `.gitignore` (digest §8).

We should **avoid** editing `media_player.py`, `select.py`, `number.py`, etc., unless a bug fix
genuinely requires it — every edit outside `art.py` is future merge-conflict debt against `fab21`.

### Entity / push patterns for any new-or-modified entity (digest §6) — `[Technical detail]`

- **ImageEntity** (`image.py`): state *is* `image_last_updated.isoformat()`; the frontend refetches
  only when that timestamp changes → bump `_attr_image_last_updated` where art actually changes,
  **never inside `async_image()`**. Call both parents with the `SamsungTVEntity` mixin;
  `ImageEntity.__init__(self, hass)` needs `hass`.
- **SelectEntity**: `options`, `current_option`, `async_select_option`.
- **NumberEntity**: `native_value`, `async_set_native_value`, bounds/step, `_attr_mode =
  NumberMode.SLIDER`.
- **Push over poll**: single-device push source → prefer entity-level websocket callbacks +
  `async_write_ha_state()`. Set `should_poll=False`; subscribe in `async_added_to_hass` via
  `async_dispatcher_connect`; unsubscribe with `async_on_remove`; broadcast art events with
  `async_dispatcher_send(hass, SIGNAL_ART_UPDATE.format(entry_id), evt)`.
- **media_source** (stretch only): if ever added, note the 2026 change —
  `BrowseMediaSource(domain=...)` is now mandatory.

---

## 5. Phased plan

Each phase has an **acceptance gate** (pass/fail, TV-verified where noted). A phase is not "done"
until its gate passes; the agent team loops on failure (§6). **P0 and P1 are strictly
sequential and gate everything.** Once P1 passes, **P2, P3, and P4 can partly run in parallel**
because they touch mostly separate regions of `api/art.py` — but they **share a serialized deploy
lane** (only one build is live on the real TV at a time), so integration-verify happens one branch
at a time. **P5 (gallery UX), P6 (blueprint), and P7 (contribute-back) are all core scope** (user
promoted them from stretch): P5 is parallel-capable with P2–P4, P6 depends on P2's bug-1 fix, and
P7's PRs follow each fix once it's TV-verified.

### P0 — Safety, adopt base, deploy, smoke-verify _(sequential; gates all)_
**Tasks:**
- Add `fab21` remote; pin and record the exact latest C tag.
- Back up the live install (B) to a dedicated git branch; prove restore works.
- Tree-level replace `custom_components/samsungtv_smart/` + shared assets with C's tag; retain
  `LICENSE`/`NOTICE`/SPDX headers; re-apply our doc files.
- Remove committed pyc/`__pycache__`; add `.gitignore`.
- Stand up the **git → Ark deploy** (rsync component + restart `homeassistant` container).
- Deploy; smoke-test.

**Gate (pass/fail, TV-verified):** Success criteria **1, 2, 3, 4** all pass.
**Parallelism:** mostly sequential; the backup-branch task can run in parallel with the
remote/tag-pin task.

### P1 — Baseline-verify C's features on the real TV _(sequential; gates P2–P4)_
**Tasks:** exercise C's art dropdown, selects, numbers, reboot button, thumbnail view, and
token-notify against `media_player.living_room_tv`. Record current-firmware behavior — especially
which of the four firmware bugs actually reproduce on *this* panel (some may already be latent).

**Gate:** Success criteria **5, 6** pass; a written baseline note captures which bugs reproduce.
**Parallelism:** verification of independent entity groups (selects vs numbers vs art dropdown)
can run in parallel read-only; no deploys here.

### P2 — Firmware-compat fixes (bugs 1–4) with tests _(parallel-capable after P1)_
**Tasks (digest §5, all in `api/art.py`):**
- Bug 1: three-tier `on()` / `is_artmode()` / `in_artmode()` (trust art-WS
  `get_artmode_status`, not REST).
- Bug 2: read `matte_list` **or** `matte_type_list`.
- Bug 3: `data.get('value', data.get('status','off'))`.
- Bug 4: detect real format via `PIL Image.open().format`; map jpg/jpeg/mpo→jpeg; send `"jpg"` on
  the wire.
- One regression test per bug (reproduce-then-fix).

**Gate:** Success criteria **7, 8, 9, 10, 15** pass; **16** (no regression of 4–6).
**Parallelism:** the four bug fixes are near-independent edits and can be authored by parallel
implementer agents on separate branches, but merge + deploy is serialized through the shared
deploy lane; TV-verify one merged build at a time.

### P3 — Dedup + sidecar map + upload type detection + batch throttle _(parallel-capable after P1)_
**Tasks (digest §5, features 5–6 + upload type detection):** perceptual dedup (grayscale→resize 384×216→GaussianBlur(2)→
diff ≤ 1.0), `content_id ↔ source-file` sidecar JSON (skip unchanged; never touch `SAM-F####` /
`MY-F####`), and the ~2 s batch throttle. (Upload type detection overlaps bug 4 — coordinate so
it's implemented once.)

**Gate:** Success criteria **11, 12, 13, 15** pass; **16** no regression.
**Parallelism:** dedup/sidecar and throttle are separable; can parallelize with P2 and P4 subject
to the serialized deploy lane. Flag the P3↔P2 overlap on upload type detection to avoid double work.

### P4 — WebSocket auto-reconnect / keepalive _(parallel-capable after P1)_
**Tasks (digest §5, feature 7):** add ping keepalive + backoff reconnect to the receive loop so a
dropped/closed WS auto-recovers; make `open()` non-lazy where needed. No reference lib has this —
this is the flagship differentiator.

**Gate:** Success criterion **14** passes (kill-WS-mid-session recovers < 60 s; idle ≥ 10 min
survives); **15, 16**.
**Parallelism:** independent region of `art.py`; parallel-capable with P2/P3 via the shared deploy
lane. Because a reconnect bug can wedge the live connection, its TV-verify should get an isolated
deploy slot (don't co-deploy with another risky branch).

### P5 — Gallery / browse UX _(core; parallel-capable with P2–P4)_
**Tasks:**
- Expose the art library as a **`media_source`** so it's browsable as a real thumbnail grid in
  HA (note 2026 change: `BrowseMediaSource(domain=...)` mandatory). Reuse C's `http_thumbnail.py`
  view to serve the grid images (no base64).
- Add **`TheScubaDiver/camera-gallery-card`** (87★, MIT, media_source-driven, visual editor) as
  the browse-and-pick card, alongside/replacing the older `folder-gallery-card`. Provide a
  ready-to-paste Lovelace example wired to the Frame.

**Gate:** Success criterion **17** passes (art library browsable as a thumbnail grid on the
dashboard; picking an image selects it on the TV within 10 s); **15, 16** hold.
**Parallelism:** mostly frontend + a read-only `media_source.py`; independent of the `art.py`
work, so parallel-capable with P2–P4 (still shares the serialized deploy lane for the
`media_source.py` piece).

### P6 — Presence-aware auto-art blueprint _(core; after P2, parallel with P3–P5)_
**Tasks:**
- Ship an installable HA **blueprint**: presence-aware `KEY_RIGHT` native-cycle art rotation +
  self-recovery (only re-assert art mode when a room presence/motion sensor says occupied),
  inspired by `sharkpunch5/frametv`. Nobody has published a Frame-art blueprint — this is novel.
- Use the fixed art-mode detection (P2 bug 1) so recovery is reliable on 2025 firmware.
- The blueprint must be **TV-agnostic**: the target Frame (media_player + its presence sensor) is a
  per-instance input, so it works on **both** Frames and is **selectable per-TV** — verify one
  automation instance on the living-room Frame and a second on the kitchen Frame.

**Gate:** Success criterion **18** passes (blueprint imports cleanly, rotates art on **each Frame**
— living room AND kitchen, as separate per-TV automation instances — on schedule, and only recovers
art mode when presence is detected).
**Parallelism:** depends on P2 bug 1 landing; otherwise independent (a YAML blueprint + docs).

### P7 — Contribute-back PRs _(core; after each contributing fix is proven on the TV)_
**Tasks:**
- Open **best-effort public PRs** to `TheFab21/ha-samsungtv-smart` for the firmware fixes (P2),
  dedup/upload (P3), and reconnect (P4) — each as a focused, independently-reviewable PR with its
  regression test. Assume no coordination and that they may never merge; our fork stays the
  deployed artifact regardless.

**Gate:** Success criterion **19** passes (a PR per proven improvement is opened upstream with
tests and a clear description; links recorded in the repo).
**Parallelism:** each PR follows its source phase (P2/P3/P4) once that fix is TV-verified; does not
block any other phase.

---

## 6. Agent-team execution model

**Plain English.** A coordinator agent runs the show and hands work to specialists. Within a
phase, specialists that don't collide run at the same time; the coordinator keeps them on a loop —
build it, put it on the real TV, check it, review it, and either advance or kick it back — until
that phase's acceptance gate goes green. You watch it all live in Herdr on the desktop and Moshi on
your phone.

**Roles**
- **Coordinator** — owns the phase gate, the task list, and the serialized deploy lane; decides
  parallel vs sequential; kicks failed work back to the implementer.
- **Researcher** — resolves any code-location/line-number drift (the digest warns line numbers are
  approximate) and re-verifies §5 claims against C after adoption, before implementers edit.
- **Planner** — turns each phase into concrete tasks/subtasks with the acceptance sub-checks.
- **Implementer(s)** — one per parallelizable workstream (e.g. bug 1, bug 2, dedup, reconnect), on
  separate branches; each writes tests-first for its slice.
- **Reviewer** — code review before deploy: license headers intact, changes confined to `art.py`/
  helpers, no stray edits to C's files, no new `.pyc`.
- **Tester-on-real-TV** — drives `media_player.living_room_tv` via HA services and reads entity
  states to confirm the phase's TV-verified criteria (see §7 for safety).
- **Deployer** — owns the one serialized deploy lane: backup-branch check → rsync → restart
  container → confirm clean load, one build at a time.

**Per-phase loop (repeat until gate green):**
`plan → implement (tests first) → review → deployer takes the lane → deploy to Ark → tester
verifies on the real TV → pass ⇒ advance / fail ⇒ coordinator kicks back with the failing
criterion.`

**Parallel-where-safe rule.** Independent `art.py` regions (P2 bugs, P3 features, P4 reconnect)
are authored in parallel, but **only one build is live on the TV at a time** — the deployer
serializes integration-verify. Risky branches (reconnect) get an isolated deploy slot.

**Visibility.** The coordinator + leads launch into their own Herdr spaces (visible in the desktop
sidebar and Moshi) via the herdr-agent-teams pattern, so the whole run is watchable/steerable from
desktop and phone while the mailbox/task-list control stays intact.

---

## 7. Test & verification strategy

**Plain English.** Two layers: fast automated tests that run without the TV (proving each bug fix
and the reconnect logic in isolation), and live checks on your actual Frame TV for anything that
only the real hardware can prove. We always back up before we touch the live TV.

### Automated (no TV) — `[Technical detail]`
- **Regression test per firmware bug (§2.7–2.10).** Each first reproduces the old failure against
  a mocked art-WS payload / REST response, then asserts the fix:
  - Bug 1: mock REST `PowerState="standby"` + art-WS `get_artmode_status="on"` ⇒ `in_artmode()` true.
  - Bug 2: payloads with `matte_list` and with `matte_type_list` ⇒ both parse non-empty.
  - Bug 3: payloads keyed `status` and keyed `value` ⇒ correct on/off.
  - Bug 4: JPEG/PNG/MPO bytes + a wrong caller hint ⇒ correct detected format and `"jpg"` wire type.
- **Dedup unit tests.** Two visually-identical-after-re-encode images ⇒ diff ≤ 1.0 (match); two
  different images ⇒ diff > 1.0 (no match). Sidecar: unchanged folder ⇒ 0 uploads; `SAM-F####`/
  `MY-F####` entries never selected for delete/modify.
- **Throttle test.** Assert ≈2 s spacing enforced across a simulated > 25-image batch.
- **Reconnect test.** Simulate a WS close mid-session ⇒ receive loop triggers backoff reconnect
  and recovers; idle keepalive ping is emitted on schedule.
- Run in CI/local; **no committed `.pyc`** (criterion 15).

### Live (real Frame TV `media_player.living_room_tv`)
The **tester-on-real-TV** agent drives the TV through HA (service calls) and observes entity states
and, where possible, the physical panel:
- Call the art-select / art-upload / matte services; read back the art-select `current_option`,
  `get_artmode` state, matte list, and `frame_art_last_result` (base64 already stripped).
- Dedup live check: run the same batch twice, confirm TV art count unchanged on run 2.
- Throttle live check: upload a > 25-image batch, confirm zero failures.
- Reconnect live check: force a disconnect (e.g. reboot via the Reboot-TV button, or drop the WS)
  and time recovery < 60 s with no HA restart.
- **Safety:** never delete Samsung-Store (`SAM-F####`) or other-tools (`MY-F####`) art; prefer
  non-destructive reads; do risky writes on a small known test image set.

### Backup discipline
- **Before any redeploy**, the live install is captured to a dedicated git branch (criterion 3),
  and restore is proven once in P0.
- Deploy = rsync component + restart `homeassistant` container; if a deploy load-errors, the
  deployer restores the backup branch and redeploys.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| **We adopt a live upstream we don't control (C keeps moving; C may change `art.py` under us).** | Pin the **exact** C tag at adoption; track `fab21` as a remote for *deliberate* syncs, never auto-pull. Researcher re-verifies §5 claims against C's actual `art.py` before implementers edit (C may already have touched some). |
| **Config-entry / entity migration on the real TV** — new SELECT/NUMBER/BUTTON entities and IP-control pairing appear on first load of C. | Treat P0 as a migration: back up B first, deploy to the real TV, watch the HA log for entity/registry churn and the IP-control pairing prompt, and confirm `media_player.living_room_tv` survives (criterion 4). If IP-control pairing needs a TV-side accept, capture that in the P0 runbook. |
| **Deploy breaks the live TV / HA won't start.** | Serialized deploy lane, one build at a time; backup-branch restore proven in P0; deployer restores on any load-error. Risky branches (reconnect) get isolated deploy slots. |
| **Reconnect logic wedges the live WS.** | Tests-first for reconnect; isolated deploy slot; bounded backoff so a failing reconnect can't hot-loop; Reboot-TV button remains the manual recovery. |
| **Firmware bugs don't reproduce on our panel** (so a "fix" is unverifiable live). | P1 records which bugs reproduce on this firmware; unverifiable-live bugs still ship with **automated regression tests** as the proof, noted as such. |
| **Deployed ≠ GitHub drift returns** (root cause of past confusion, digest §8). | Ban hand-editing on the server; git → Ark rsync is the only deploy path; the live install is only ever a checkout of a branch. |
| **Contribute-back PRs stall / diverge.** | Best-effort only; our fork is always the deployed artifact and must stand alone (non-goal §3). |
| **Committed `.pyc` / stale caches cause "works on server, not in git" ghosts.** | Remove the 17 committed pyc files, add `.gitignore`, verify clean tree in P0 (criterion 15). |

---

## 9. Dependencies & licensing

- **C (TheFab21) base — Apache-2.0.** Adopting the tree is license-clean. Retain C's `LICENSE`
  and `NOTICE`, keep per-file SPDX headers, and preserve attribution. Our fork is Apache-2.0.
- **`api/art.py` — `SPDX-License-Identifier: LGPL-3.0`** (derived from xchwarze). Copying/reusing
  LGPL reference code (e.g. NickWaterton's dedup/`on()`-tiering patterns) into this file is clean
  **as long as the LGPL-3.0 header and attribution stay**. Keep them.
- **Runtime deps:** `Pillow` (PIL) is already required for the thumbnail view and is reused for
  upload type detection and the 384×216 dedup thumbnail — **no new heavy dependency introduced**.
- **Reference-only (not vendored):** `janstrm` (MIT, entity reference), `TheScubaDiver/
  camera-gallery-card` (MIT, stretch), `sharkpunch5/frametv` (blueprint inspiration). Anything we
  actually copy carries its origin license and attribution.

---

## 10. Open questions

Most decisions are settled (§1). Only these may need your input:

1. **Exact C tag to pin.** Master is 8.3.3; tags go to 8.24. Default plan: pin the **latest
   release tag** at execution unless you'd rather pin master. (Recommend: latest tag — more stable
   than master.)
2. **IP-control pairing on the real TV.** C adds an IP-control channel that may prompt the TV to
   accept a new pairing on first load. Are you OK physically accepting a prompt on the Frame during
   the P0 deploy if it appears? (Recommend: yes, once, during a supervised P0 deploy.)
3. **Contribute-back timing — DECIDED.** Planned as **P7**, one PR per improvement, opened once
   that fix is TV-verified (user approved planning it in from the start).
4. **Gallery card + blueprint — DECIDED.** Both promoted to **core scope** (P5 gallery UX, P6
   blueprint) per user direction 2026-07-12.
