# Frame TV / Art Mode — Research Digest

_Compiled 2026-07-12. Source of truth for the "best-in-class Art Mode" effort. Downstream
agents: read this instead of re-researching. Every claim here was gathered by dedicated
research agents and cross-checked; line numbers are approximate and must be re-verified before
editing code._

## 1. The lineage (settled)

Linear GitHub fork chain, single root:

```
roberodin/ha-samsungtv-custom      132★  last push 2023-07  (root, DEAD)
 └ xchwarze/ha-samsungtv-custom     45★  2020-10  (DEAD, stripped to nothing)
   └ jaruba/ha-samsungtv-tizen     316★  2022-12  (DEAD; channel-logos feature)
     └ ollo69/ha-samsungtv-smart   658★  2026-05  (last release v0.14.5 Aug-2025; only art on/off)
       └ chansearrington/ha-samsungtv-smart   (OUR fork "A", manifest 6.3.2)
```

Detached sibling, **now the leading fork**:
- **TheFab21/ha-samsungtv-smart ("C")** — Apache-2.0, manifest 8.3.3, tags up to 8.24, last push
  2026-07-10. `parent:null`, `fork:false` → history detached, NOT in A's fork network (GitHub
  compare 404s), so it CANNOT be merged via PR — code must be copied tree-level.

**Verdict on the dead ancestors (roberodin/xchwarze/jaruba): ignore entirely.** ollo69 already
absorbed everything valuable (incl. jaruba's channel logos). Nothing to salvage.

## 2. The three versions of our codebase

| | A = chansearrington (GitHub) | B = live install on Ark | C = TheFab21 (leading) |
|---|---|---|---|
| Manifest version | 6.3.2 | 0.14.5 | 8.3.3 (tags → 8.24) |
| Where | `/Users/chansearrington/GitHub/personal/ha-samsungtv-smart` | Ark `/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart` (copy in scratch `ark-installed/`) | remote `fab21` (added), raw github |
| Status | 27 commits ahead of ollo69, 3 behind | oldest; hand-patched; has `.bak` files | **strict superset of A; A's art code was written by TheFab21** |

**Feature completeness: C > A > B.** A has **nothing functional** that C lacks. B's French
"corrections" (`README_CORRECTIONS.md`: strip base64 from `frame_art_last_result` via
`_store_art_result()`, skip-existing-file download) are **already in both A and C** (C
`media_player.py` ~L3271, ~L3949). Both A and C are **Apache-2.0** → adopting C is license-clean
(retain C's LICENSE/NOTICE + headers).

## 3. DECISION (user, 2026-07-12)

- **Adopt C (TheFab21 latest) as the new base** via tree-level replacement of
  `custom_components/samsungtv_smart/` + shared assets.
- Keep it as **our own deployable fork**, tracking `fab21` as an upstream remote for future syncs.
- Re-apply our only unique files if desired: `README_CORRECTIONS.md`, `README_OAUTH2.md`.
- **Contribute improvements back to TheFab21 as best-effort public PRs** — user has **no
  relationship** with TheFab21, so do NOT assume coordination or that PRs get merged; our fork
  stays the deployed artifact.
- Do **NOT** rebuild entities ourselves (the `janstrm` MIT repo is only a reference; C already
  ships working select/number/button/image-ish platforms).

## 4. What C already ships (so we DON'T rebuild it)

- `api/ipcontrol.py` — Samsung JSON-RPC control channel (port 1516); survives reboots;
  independent of the Art WebSocket.
- `select.py` (~1717 lines) — **11 selects**: Color Tone, Speaker Output, SmartThings Media
  Output, Matte Type, Matte Color, Picture Mode, Art Motion Sensitivity, Art Motion Timer, Art
  Brightness Sensor.
- `number.py` (~806) — **5 numbers**: IP Backlight (0–50), IP Picture, Art Brightness (0–100),
  Art Color Temperature (−5..+5).
- `button.py` (~141) — **Reboot TV** over IP control (recovers a hung Art WebSocket).
- `http_thumbnail.py` (~140) — on-demand resized-thumbnail HTTP view
  `/api/samsungtv_smart/thumbnail?path=…&w=…`, disk-cached JPEG q78, path-traversal guarded.
  **This replaces the base64-in-attribute bloat.** Registered in `__init__.py` ~L1060.
- `token_notify.py` (~134) — self-clearing FR/EN notifications for bad WS / IP-control tokens.
- Newer `folder-gallery-card.js` (points `<img>` at the thumbnail endpoint), longer
  `Frame_Art.md`, `SmartThings_API_Usage.md`, `IP_Control_Protocol_Reference.md`.
- `media_player.py` ~4538 lines (superset of A's 3021), more sophisticated power-state logic.

## 5. The GENUINELY NOVEL work — nobody has solved these (our differentiators)

Even C does not have these. This is where we add real value and lead the ecosystem. All apply to
the vendored async art client `custom_components/samsungtv_smart/api/art.py` (already
`SPDX-License-Identifier: LGPL-3.0`, derived from xchwarze → copying LGPL code in is clean if the
header/attribution stays). **Re-verify these against C's art client after adoption — C may have
touched some.**

### Firmware-compat BUGS (small fixes, high impact)
1. **2025 Frame art-mode misdetection (LIVE BUG).** REST reports `PowerState="standby"` while Art
   Mode is ON (xchwarze #185, model TQ50LS03FAUXXC). Our `is_artmode()` (art.py ~L373) requires
   `on()` (~L358) which needs REST `PowerState=="on"` → wrongly reports not-in-art-mode; may
   refuse select/upload. **Fix:** adopt NickWaterton's three-tier
   `on()` (REST, cheap) / `is_artmode()` (cached event flag) / `in_artmode()` =
   `on() OR get_artmode()=='on'` (authoritative). Trust the art WS `get_artmode_status`, not REST.
2. **Matte list empty on some firmware.** Field `matte_type_list` was renamed `matte_list`. Our
   `get_matte_list()` (~L848) reads only `matte_type_list`. **Fix:** read either (xchwarze does).
3. **Art-status field rename.** API 5.x uses `status` not `value`. Our `get_artmode()` (~L796)
   reads `value` only. **Fix:** `data.get('value', data.get('status','off'))` (NickWaterton).
4. **Upload type detection weak.** `upload()` defaults `file_type="png"`; bytes inputs with wrong
   caller hint fail. **Fix:** detect real format via `PIL Image.open().format`; map
   jpg/jpeg/mpo→jpeg; note wire quirk: `send_image` wants `"jpg"` not `"jpeg"`.

### Feature gaps
5. **No dedup → re-uploads every time.** Adopt the ecosystem-standard perceptual match: grayscale
   → `resize((384,216))` → `GaussianBlur(2)` → `ImageChops.difference`, normalized `diff<=1.0`
   (the TV re-encodes uploads so hashes never match). Plus a **content_id ↔ source-file sidecar
   JSON** (`{filename:{content_id,modified:mtime}}`) so re-runs skip unchanged files and never
   touch Samsung-Store (`SAM-F####`) or other tools' art (`MY-F####`).
   (Source: NickWaterton `example/web_interface/async_art_gallery_web.py`.)
6. **No batch upload throttle.** Empirically needs ~2 s between images; batches >25 fail without
   it. Add a throttle.
7. **No WebSocket reconnect/keepalive.** No reference lib (xchwarze OR NickWaterton) has this — a
   shared weakness. Our `_receive_loop` just exits on close; `open()` is lazy. **Add ping +
   backoff reconnect → genuine differentiator.**

### Explicitly do NOT do
- **Do NOT add 16:9 / 3840×2160 resizing before upload.** Nobody does it; raw bytes is correct;
  the TV + matte handle fitting. The only PIL resize upstream is the 384×216 dedup thumbnail.

## 6. Home Assistant implementation patterns (for any new/modified entities)

Grounded in current (2026) HA core. Our integration already forwards platforms in
`__init__.py` (`SAMSMART_PLATFORM`) and uses `hass.data[DOMAIN][entry_id]`; base entity is
`SamsungTVEntity` in `entity.py`. Adding a platform = extend that list; unload already handles it.

- **ImageEntity** (`image.py`): state IS `image_last_updated.isoformat()`. Frontend refetches
  ONLY when that timestamp changes — bump `_attr_image_last_updated` wherever art actually
  changes, **never inside `async_image()`**. `ImageEntity.__init__(self, hass)` needs `hass`;
  call both parents explicitly with the `SamsungTVEntity` mixin. Ref: core `roborock/image.py`
  (`RoborockMapQ10` push variant), `fully_kiosk/image.py` (lazy fetch).
- **SelectEntity** (`select.py`): `options`, `current_option`, `async_select_option`. Ref:
  `switchbot_cloud/select.py`, `roborock/select.py`.
- **NumberEntity** (`number.py`): `native_value`, `async_set_native_value`, bounds/step,
  `_attr_mode = NumberMode.SLIDER`. Ref: `switchbot/number.py`.
- **Push updates**: prefer entity-level websocket callbacks + `async_write_ha_state()` over a
  polling `DataUpdateCoordinator` (single-device push source). Set `should_poll=False`; subscribe
  in `async_added_to_hass` via `async_dispatcher_connect`, unsubscribe with `async_on_remove`;
  broadcast art events with `async_dispatcher_send(hass, SIGNAL_ART_UPDATE.format(entry_id), evt)`.
- **media_source** (optional, second-phase): browsable art library grid; note 2026 change —
  `BrowseMediaSource(domain=...)` is now mandatory.

## 7. Ecosystem projects worth leveraging / inspiration

- **LEVERAGE:** C = TheFab21 (the base). `janstrm/…Frame-Art-Director-Integration` (MIT) — entity
  reference only. `TheScubaDiver/camera-gallery-card` (87★, MIT) — best maintained gallery card,
  media_source-driven, has a visual editor; better than the dead `folder-gallery-card` lineage.
- **INSPIRATION:** `sharkpunch5/frametv` — presence-aware `KEY_RIGHT` native-cycle recovery loop +
  combined-state sensor (flagship blueprint idea — nobody has published a Frame-art blueprint).
  `chermeschaterne/ha-samsung-frame-art-rotator` (MIT) — 2023+ WS quirks checklist.
  `s3lfish/the-frame-machine` (MIT) — self-healing scheduler + WOL/MAC discovery reliability model.
  `slknijnenburg/framegallery`, `mcsdodo/samsung-frame-art-gallery` — matte-vs-crop rules,
  live pre-upload preview (only if we ever add crop UX).
- **HA core** `samsungtv` integration has ZERO art support → open field.

## 8. Live environment (ground truth, verified 2026-07-12)

- Ark reachable via `ssh ark` (The-Ark). HA = docker container `homeassistant`
  (lscr.io/linuxserver/homeassistant), config at host `/mnt/user/appdata/homeassistant`.
- Integration **loads cleanly, zero errors** — only HA's standard "custom integration" notice.
  Entities incl. `media_player.living_room_tv` (the Frame) and `media_player.kitchen_smartthings_hub`;
  automation `frame_tv_mount_position_sync` (motorized MantelMount). Recurring cosmetic warning
  "SmartThings report TV is off but status detected is on" — known noise, not a failure.
- Deployed copy (B) differs from A: config_flow 722, sensor 573, media_player 466, switch 399,
  __init__ 255 changed lines; version 0.14.5. `.bak` files present → history of hand-editing on
  the server. **Root cause of "I thought I used it… maybe I don't":** deployed ≠ GitHub.
- **17 compiled `__pycache__/*.pyc` are committed to A** — must be gitignored + removed.

## 9. Deployment / workflow

- Stop hand-editing on the server. Establish **git → Ark deploy** (rsync the component to
  `/mnt/user/appdata/homeassistant/custom_components/samsungtv_smart`, restart the `homeassistant`
  container) as the only path. HACS custom-repo install is the nicer long-term option (do later).
- Always back up the live install to a git branch before any redeploy.
- Test target: the real Frame `media_player.living_room_tv` on Ark.
