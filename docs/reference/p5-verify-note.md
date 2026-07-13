# P5 TV-verify note (2026-07-12) — gallery browse UX

Merged `p5-gallery`; deployed. **Deploy-caught bug fixed:** media_source silently disabled because
`BrowseError` was imported from `media_source` (moved to `media_player.errors` in HA 2026.7) and an
over-broad `except ImportError` swallowed it. Fixed → redeployed.

| Criterion | Result |
|---|---|
| 17 — gallery browsing (backend) | ✅ HA media library shows **"Samsung Frame Art"** → expands to **both Frames** (Living Room + Kitchen) via WS `media_source/browse_media`. Per-Frame art grid enumerated from `art.available()`, tiles served by the existing http_thumbnail view (no base64). |
| 17 — gallery UI (frontend) | ⏳ FOLLOW-UP with user: install `camera-gallery-card` via HACS + add the dashboard example (`docs/gallery/`), and pre-fetch tile thumbnails via `art_get_thumbnails_batch` (un-fetched tiles 404 until then). Tap-to-select uses `art_select_image` service (no native art-select entity). |
| 15/16 | ✅ 29 passed/1 skipped; 0 pyc; core integration + both Frames healthy post-fix |

Plan corrections made by the P5 agent (verified): thumbnail path scheme (view resolves a www file,
not a `?path=content_id` query); pick action uses `art_select_image` service.
