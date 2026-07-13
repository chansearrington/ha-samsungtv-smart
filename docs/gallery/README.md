# Frame Art gallery card

Browse each Frame's art library as a thumbnail grid in Lovelace and tap a tile to
put it on the TV.

A ready-to-run **"Frame Art" dashboard** is already live on the HA instance at
url path **`/frame-art`** (one view per Frame). Its exact config is exported to
[`frame-art-dashboard.yaml`](./frame-art-dashboard.yaml).

## What powers this

This integration ships a `media_source` (`custom_components/samsungtv_smart/media_source.py`)
that HA registers under the domain `samsungtv_smart`, so it is browsable at:

```
media-source://samsungtv_smart
```

Browsing is two levels deep:

1. **Root** — one directory per configured Frame (e.g. *Living Room TV*, *Kitchen TV*).
2. **A Frame** — that Frame's art library, one image tile per artwork. Its content
   id is `media-source://samsungtv_smart/<entry_id>`.

Each tile's thumbnail is served by the integration's existing HTTP view
(`/api/samsungtv_smart/thumbnail?path=…&w=…`), which returns a small cached JPEG
of the file the `frame_art` coordinator saved under
`www/frame_art/<entry_id>/<subdir>/<content_id>.jpg`. **No base64** is produced —
the grid only moves kilobytes per tile.

## Two cards, two jobs (important — verified against the live cards)

There is no single card that both browses the `media_source` **and** taps-to-select
art. The two requirements are split across two cards:

| Card | Source | Tap to display on Frame? |
|------|--------|--------------------------|
| **folder-gallery-card** (integration's own, `v1.5.0`) | on-disk thumbnail files (`image_list`) | **Yes** — calls `samsungtv_smart.art_select_image` |
| **camera-gallery-card** (`TheScubaDiver`, `v3.1.0`, MIT) | `media-source://samsungtv_smart/<entry_id>` | **No** — browse/preview only |

- `folder-gallery-card` is auto-registered by the integration at
  `/api/samsungtv_smart/folder-gallery-card.js` (no HACS needed). It reads a static
  `image_list` (or a folder sensor) and taps to select — this is the working
  selection gallery.
- `camera-gallery-card` v3.1.0 uses `source_mode: media` + `media_sources:` and is
  great for dynamically browsing the *whole* library from the media_source, but it
  has **no** `tap_action`/`call-service` option and no `columns` — the earlier
  `camera-gallery-card-example.yaml` assumed features this card does not have.

## What was installed / done on the live instance (2026-07-12)

1. **camera-gallery-card** downloaded from the GitHub release asset
   (`v3.1.0`, MIT) to
   `www/community/camera-gallery-card/camera-gallery-card.js` on the HA host:

   ```
   curl -sL https://github.com/TheScubaDiver/camera-gallery-card/releases/download/v3.1.0/camera-gallery-card.js \
     -o /config/www/community/camera-gallery-card/camera-gallery-card.js
   ```

   (There is no `dist/` in the repo; the built JS only exists as a release asset.)

2. **Lovelace resource registered** (WS `lovelace/resources/create`):

   ```
   url:  /local/community/camera-gallery-card/camera-gallery-card.js
   type: module
   ```

3. **Thumbnails pre-fetched** with `samsungtv_smart.art_get_thumbnails_batch`,
   targeting each Frame's **media_player** entity (the service is registered on the
   media_player platform, target `entity: integration: samsungtv_smart`):

   ```yaml
   service: samsungtv_smart.art_get_thumbnails_batch
   target:
     entity_id: media_player.living_room_tv        # or media_player.kitchen_smartthings_hub
   ```

   Thumbnails land under `www/frame_art/<entry_id>/{personal,store,other}/<content_id>.jpg`
   and are verifiable via the HTTP view returning `200 image/jpeg`:

   ```
   /api/samsungtv_smart/thumbnail?path=/local/frame_art/<entry_id>/store/<content_id>.jpg&w=200
   ```

   **The Frame must be reachable for its art API when you run the batch.** If the
   TV is off you get `frame_art_last_result: {"error": "Frame TV not supported"}`
   and nothing new is downloaded — re-run the batch with the Frame on.

4. **Dedicated dashboard created** (WS `lovelace/dashboards/create` +
   `lovelace/config/save`) at url path `/frame-art`, one view per Frame. Existing
   dashboards were left untouched.

## Tap-to-select mechanism

There is **no `select` entity** for artwork. Art is chosen with the
`samsungtv_smart.art_select_image` service (`content_id` field). folder-gallery-card
derives `content_id` from the thumbnail filename (extension stripped) and dispatches:

```yaml
tap_action: action
action:
  service: samsungtv_smart.art_select_image
  target:
    entity_id: media_player.living_room_tv
  data:
    content_id: "{{content_id}}"
    show: true
```

## Keeping the folder-gallery `image_list` fresh

folder-gallery-card renders exactly the files listed in `image_list` — a snapshot
of what was on disk when the dashboard config was written. After you favorite new
art and re-run `art_get_thumbnails_batch`, add the new
`/local/frame_art/<entry_id>/<subdir>/<content_id>.jpg` paths to the card's
`image_list` (or switch it to a `folder` platform sensor exposing `file_list`).
The camera-gallery-card "browse" card always reflects the full live library with no
edits.

## Update 2026-07-12 — camera-gallery-card removed (config error fix)

`camera-gallery-card` was removed from the `/frame-art` dashboard (both Frame views) and its
Lovelace resource deleted. It **requires `path_datetime_format`** to group files by date and is
built for date-stamped camera footage — a poor fit for art thumbnails (no dates in their paths),
which produced a "Configuration error" card. The **folder-gallery-card** provides the working
tap-to-display gallery. For dynamic full-library browsing, use Home Assistant's native **Media**
panel → "Samsung Frame Art" (the `media_source` is still registered and works).
