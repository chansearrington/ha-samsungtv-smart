# Frame Art gallery card

Browse each Frame's art library as a thumbnail grid in Lovelace and tap a tile to
put it on the TV.

## What powers this

This integration ships a `media_source` (`custom_components/samsungtv_smart/media_source.py`)
that HA registers under the domain `samsungtv_smart`, so it is browsable at:

```
media-source://samsungtv_smart
```

Browsing is two levels deep:

1. **Root** — one directory per configured Frame (e.g. *Living Room TV*, *Kitchen TV*).
2. **A Frame** — that Frame's art library, one image tile per artwork.

Each tile's thumbnail is served by the integration's existing HTTP view
(`/api/samsungtv_smart/thumbnail?path=…&w=…`), which returns a small cached JPEG
of the file the `frame_art` coordinator already saved under
`www/frame_art/<entry_id>/<subdir>/<content_id>.jpg`. **No base64** is produced —
the grid only moves kilobytes per tile.

## Install the card

Install **`camera-gallery-card`** (MIT) via HACS as a custom repository:

- HACS → Frontend → ⋮ → Custom repositories
- Repository: `https://github.com/TheScubaDiver/camera-gallery-card`
- Category: *Lovelace*

It is `media_source`-driven and has a visual editor. It replaces the older
`folder-gallery-card` this integration used before.

## Use it

Paste [`camera-gallery-card-example.yaml`](./camera-gallery-card-example.yaml)
into a dashboard (Edit dashboard → Add card → Manual). It points at
`media-source://samsungtv_smart` and wires tap-to-select through the real
`samsungtv_smart.art_select_image` service. Duplicate the card per Frame,
pointing each card's `tap_action` target at that Frame's `frame_art` sensor.

## Important notes / dependency

- **There is no `select` entity for artwork.** Art is chosen with the
  `samsungtv_smart.art_select_image` service (`content_id` field). The example
  uses exactly that.
- **The content-id list is always complete**, but a tile only has a real image
  once its thumbnail has been fetched to disk. The coordinator auto-fetches only
  the *currently displayed* artwork; run the `samsungtv_smart.art_get_thumbnails_batch`
  service once to pre-populate the whole library so every tile shows an image.
  Until then, un-fetched tiles resolve to a 404 in the thumbnail view.
- On TV-verify (Task 5.3), confirm the exact `frame_art` sensor entity ids and
  confirm what variable the card passes to `tap_action` (the media identifier is
  `<entry_id>/<content_id>`; strip the prefix with
  `"{{ media_content_id.split('/')[-1] }}"` if the card hands you the whole thing).
