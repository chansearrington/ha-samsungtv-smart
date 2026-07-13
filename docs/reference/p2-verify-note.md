# P2 TV-verify note (2026-07-12) — firmware-compat fixes

Merged `p2-firmware-fixes`; deployed to Ark; verified on BOTH Frames.

| Criterion | Result |
|---|---|
| 7 — bug1 art-mode detection (`in_artmode()`) | ✅ regression test passes; live standby-path not forced (firmware-specific, test-backed) |
| 8 — bug2 matte list | ✅ regression test (both field names); live matte_type still 10 options on both Frames |
| 9 — bug3 art-status field (`value`/`status`) | ✅ regression test (both shapes + empty-dict→off) |
| 10 — bug4 upload type via PIL | ✅ regression test (JPEG/PNG/MPO + wrong hint) |
| 15 — tests green, no pyc | ✅ 12/12 passed; 0 committed pyc |
| 16 — no regression (4–6) | ✅ integration loads clean; matte selects populated on both Frames; no unexpected log errors |

Adaptations from plan (verified): bug3 guard changed `if data:`→`if data is not None:` so empty `{}`→"off";
bug4 detection safely falls back to caller hint if `file` isn't bytes. Deploy clean (no samsungtv errors).
