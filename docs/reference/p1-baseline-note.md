# P1 baseline verification (2026-07-12) — BOTH Frames

Verified live via HA API (http://192.168.1.143:8123) against both Frames.

## Platforms present (criterion 6) — ✅ both Frames
Living Room (`media_player.living_room_tv`) and Kitchen (`media_player.kitchen_smartthings_hub`)
each expose the new best-in-class entities, all instantiated without error:
- `select .*_matte_type` — 10 options (none, modernthin, modern, modernwide, flexible, shadowbox, …)
- `select .*_matte_color` — 16 options
- `select .*_picture_mode` — LR: Dynamic/FILMMAKER MODE/Movie/Standard (4); Kitchen: EyeComfort/Optimized (2) → **different firmware between the two Frames**
- `select .*_motion_sensitivity` (1–3), `.*_motion_timer` (off/5/15/30/60/120), `.*_brightness_sensor` (off/on)
- `number .*_art_mode_brightness`, `.*_art_mode_color_temperature`
- `switch .*_art_mode`, `sensor .*_frame_art` (attrs: tv_power_state, art_mode_status,
  current_content_id, current_matte_id, current_thumbnail_url, slideshow_status)

## Controllability (criterion 4) — ✅ proven live
Called `switch.turn_on` on `switch.living_room_tv_art_mode` → HTTP 200; TV entered Art Mode;
switch `off→on`, sensor `off→on` (art_mode_status=on), current art `SAM-S10001061`, thumbnail
served at `/local/frame_art/<entry>/current.jpg` (640×360 JPEG). Round-trip HA→TV→HA confirmed.

## Criterion 5 nuance — no native art-picker dropdown yet
There is **no `select` entity for choosing an artwork** on either Frame (even in TheFab21 8.3.3).
Art selection today is via the folder-gallery-card / `art_select_image` service; the `frame_art`
sensor reports current art. → **Confirms P5 (media_source + camera-gallery-card browse/pick) is
genuinely needed** to satisfy "pick art from a dropdown/grid". Criterion 5 to be met by P5.

## Firmware-bug live reproduction (feeds P2)
- Bug 2 (matte list empty): **does NOT reproduce** — matte_type has 10 options, matte_color 16, on
  both Frames. Ships as test-only regression.
- Bug 1 (2025 art-mode misdetection): art mode toggled/reported correctly here (TV was `on`); the
  standby-misdetection path is firmware-specific → ships with regression test.
- Bugs 3 & 4: payload-shape/upload — test-only proof.
- **New observation:** `number.*_art_mode_brightness` stayed `unavailable` even with art mode ON —
  investigate in P2/P3 (possible art-brightness read gap on this firmware).
