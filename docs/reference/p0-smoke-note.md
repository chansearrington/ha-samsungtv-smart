# P0 smoke-verify note (2026-07-12)

Deploy of adopted base **8.3.3** to live HA on Ark (container `homeassistant`).

| Criterion | Result |
|---|---|
| 1 — base adopted cleanly | ✅ manifest 8.3.3; `art.py` byte-equal to tag; Apache-2.0 LICENSE (root) retained; LGPL-3.0 art.py header intact; no NOTICE upstream |
| 2 — deploy loads with zero errors | ✅ only HA's "custom integration" notice; unexpected samsungtv error/warning count = 0 |
| 3 — backup-before-deploy proven | ✅ `backup/live-install-B` (0.14.5) captured; restore proven byte-identical (diff exit 0) |
| 4 — TV present & controllable | ✅ present+enabled: `media_player.living_room_tv` registered, not disabled, integration set up with no error. Live control command exercised immediately in P1 Task 1.1 (art selection). |

**New entities live after adoption (44 total):** 2 media_player, 2 remote, 14 select, 4 number,
4 switch, 18 sensor. Living-room Frame now has matte-type/matte-color/picture-mode/motion/
brightness-sensor selects, art-brightness + art-color-temp numbers, art-mode switch, frame-art sensor.

**IP-control pairing prompt:** none observed in the log (no pairing/token errors for samsungtv;
the only auth error at restart was unrelated `pentair_cloud`).

**Backup branch:** `backup/live-install-B`. **Restore runbook:** `docs/reference/backup-restore-runbook.md`.
