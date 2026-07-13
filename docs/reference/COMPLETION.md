# Frame Art Best-in-Class — Completion Record (2026-07-12)

Branch `frame-art-best-in-class`, 34+ commits on TheFab21 `8.3.3` base. All work verified live on
**both** Samsung Frames on Ark HA.

## Phases (all complete + TV-verified)
- **P0** Adopt TheFab21 8.3.3 (tree-level), retain Apache-2.0 + LGPL art.py header — live, clean.
- **P1** Verify features on both Frames — art-mode toggle proven on the physical TV.
- **P2** 4 firmware-compat fixes (in_artmode/matte_list/status-field/upload-type) + 12 tests — live.
- **P3** Perceptual dedup + content_id sidecar + batch throttle + `_dedup.py` — live-loaded.
- **P4** WS auto-reconnect (bounded backoff, cap 60s) + keepalive — **destructive test PASSED live**
  (forced drop via surgical 35s iptables block on Ark; recovered ~1s; no hot-loop; firewall clean).
- **P5** `media_source` "Samsung Frame Art" (both Frames) + `/frame-art` dashboard +
  camera-gallery-card (browse) + folder-gallery-card (tap-to-select). Deploy caught & fixed a real
  HA-2026.7 `BrowseError` import bug.
- **P6** Presence-aware auto-art blueprint — imports cleanly into live HA.
- **P7** 3 best-effort PRs to TheFab21: #150 firmware, #151 dedup, #152 reconnect (fork
  `chansearrington/ha-samsungtv-smart-fab21`). Rebuilt to touch NONE of their existing files.
- **P8** (added) `art_upload_folder` service wiring `upload_batch` → dedup verified LIVE
  (run1=2 uploads, run2=0; test images cleaned up; library back to baseline).

## Parity audit (user concern: "did we lose anything?")
**No.** C (8.3.3) is a full feature-for-feature superset of both the old fork (A, 6.3.2) and the
live install (B, 0.14.5): all 19 services present (C has 21), all entities, entire art API, all 5
French hand-fixes (base64 strip, skip-existing-download, retries, no-DRM-skip, skipped counts),
folder-gallery-card (byte-identical), examples (byte-identical), docs. Only non-functional diffs:
an upstream component README (superseded) and a duplicate translations_en.json. Independently
re-verified via git comm/diff.

## Live environment / ops
- HA: docker `homeassistant` on Ark (`ssh ark`, config `/mnt/user/appdata/homeassistant`), UI
  `192.168.1.143:8123`. Deploy = `scripts/deploy_to_ark.sh` (rsync + restart). Backup branch
  `backup/live-install-B` (restore runbook in docs/reference).
- **Frame IPs (changed 2026-07-12, WiFi→Ethernet):** Living Room `192.168.1.182` (was .64),
  Kitchen `192.168.1.186` (was .140). Repointed by editing `.storage/core.config_entries`
  host+mac (stop-edit-start), confirmed by matching `:8001/api/v2/` duid to entry `data.id`.

## Optional follow-ups (documented, not blocking)
- Complete IP-control pairing to activate TheFab21's Reboot-TV button + IP backlight/picture numbers.
- Harden `upload_batch` so a sidecar-write failure after upload is non-fatal (keeps content_ids).
- Refresh folder-gallery-card `image_list` per Frame to show the full library; re-run
  `art_get_thumbnails_batch` for Kitchen to populate more tiles.
- Stale HomeKit bridge ref to non-existent `media_player.kitchen_tv` (pre-existing; unrelated).
