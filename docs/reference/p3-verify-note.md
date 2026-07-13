# P3 TV-verify note (2026-07-12) — dedup + sidecar + throttle

Merged `p3-dedup-upload`; deployed to Ark; verified.

| Criterion | Result |
|---|---|
| 11 — dedup | ✅ unit tests (identical-after-reencode ≤1.0 match; different >1.0). Live-upload verify DEFERRED (would add test art to production Frames — do in a controlled session). |
| 12 — sidecar map | ✅ unit tests (skip unchanged; SAM-F/MY-F protected; roundtrip). Live verify deferred as above. |
| 13 — batch throttle | ✅ unit test (~2s spacing / >25). Live verify deferred as above. |
| 15 — tests green, no pyc | ✅ 23/23 passed; 0 pyc |
| 16 — no regression | ✅ both Frames healthy post-deploy; `_dedup.py` parses on Ark; integration clean |

NOTE: live upload-batch verification intentionally not run against the real Frames to avoid
cluttering them with test images; pending a user-approved controlled run with a small test set + cleanup.
