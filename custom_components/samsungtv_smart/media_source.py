"""Expose the Frame TV art library as a browsable media_source thumbnail grid.

Browsing is two levels deep because there can be more than one Frame on the one
integration (e.g. Living Room + Kitchen):

    root                 -> one directory per configured Frame (config entry)
      <entry_id>         -> that Frame's art library, one image tile per artwork

Every tile's ``thumbnail`` points at the integration's existing HTTP view
(``http_thumbnail.SamsungTVThumbnailView``), which serves a small cached JPEG of
a file under ``<config>/www``. The frame_art coordinator (sensor.py) already
materializes each artwork's thumbnail on disk at
``www/frame_art/<entry_id>/<subdir>/<content_id>.jpg`` — so we reuse those files
via the view. No base64 is ever produced here.

NOTE / dependency: the coordinator only auto-fetches the *currently displayed*
artwork's thumbnail. Tiles for artworks whose thumbnail has not been fetched yet
resolve to a 404 in the view until the ``art_get_thumbnails_batch`` service has
populated the library. The content-id *list* itself is always available via the
art client, so the grid is always fully enumerated even before every thumbnail
exists on disk.
"""

from __future__ import annotations

import logging

# ``.const`` is the normal Home Assistant package import; the bare ``const``
# fallback lets the pure helpers below be unit-tested by importing this file as a
# top-level module (see tests/test_media_source.py) without a HA package parent.
try:
    from .const import DATA_ART_API, DOMAIN
except ImportError:  # pragma: no cover - bare-module import in unit tests
    from const import DATA_ART_API, DOMAIN

_LOGGER = logging.getLogger(__name__)

THUMBNAIL_VIEW = "/api/samsungtv_smart/thumbnail"
_DEFAULT_THUMB_W = 200
_RESOLVE_W = 1024  # served full-ish from the same on-disk thumbnail

# 'my pictures', favourites, and store categories the art client understands.
_ART_CATEGORY = None  # None == every category (full content_list)


# --- pure helpers (no Home Assistant dependency; unit-tested directly) --------


def _subdir_for_content(content_id: str) -> str:
    """Classify a content_id into its on-disk thumbnail subfolder.

    Mirrors sensor.py's thumbnail writer EXACTLY; if this drifts, the built URL
    points at a file that was never written there.
    """
    if content_id.startswith("MY_F"):
        return "personal"
    if content_id.startswith("SAM-"):
        return "store"
    return "other"


def _local_thumb_path(entry_id: str, content_id: str) -> str:
    """The ``/local/...`` www path where the coordinator saved the thumbnail."""
    subdir = _subdir_for_content(content_id)
    filename = f"{content_id.replace(':', '_')}.jpg"
    return f"/local/frame_art/{entry_id}/{subdir}/{filename}"


def thumbnail_url(entry_id: str, content_id: str, width: int = _DEFAULT_THUMB_W) -> str:
    """Build the HTTP-view thumbnail URL for one artwork (no base64)."""
    return f"{THUMBNAIL_VIEW}?path={_local_thumb_path(entry_id, content_id)}&w={width}"


# --- Home Assistant glue (only defined when HA is importable) -----------------

try:
    from homeassistant.components.media_player import MediaClass, MediaType
    from homeassistant.components.media_source import (
        BrowseError,
        BrowseMediaSource,
        MediaSource,
        MediaSourceItem,
        PlayMedia,
    )
    from homeassistant.core import HomeAssistant

    _HAS_HA = True
except ImportError:  # pragma: no cover - pure helpers unit-tested without HA
    _HAS_HA = False


if _HAS_HA:

    def build_art_child(entry_id: str, content_id: str, title: str) -> BrowseMediaSource:
        """One browsable, playable art tile with an HTTP-view thumbnail."""
        return BrowseMediaSource(
            domain=DOMAIN,  # 2026: mandatory
            identifier=f"{entry_id}/{content_id}",
            media_class=MediaClass.IMAGE,
            media_content_type=MediaType.IMAGE,
            title=title,
            can_play=True,
            can_expand=False,
            thumbnail=thumbnail_url(entry_id, content_id, _DEFAULT_THUMB_W),
        )

    def _art_entries(hass: HomeAssistant) -> dict[str, object]:
        """Map entry_id -> art client for every Frame that has one.

        ``hass.data[DOMAIN]`` also holds non-entry keys (e.g. the local logo
        path), so filter to dict values that actually carry an art client.
        """
        store = hass.data.get(DOMAIN, {})
        return {
            entry_id: data[DATA_ART_API]
            for entry_id, data in store.items()
            if isinstance(data, dict) and data.get(DATA_ART_API) is not None
        }

    def _entry_title(hass: HomeAssistant, entry_id: str) -> str:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry.title if entry else entry_id

    class SamsungArtMediaSource(MediaSource):
        """Browse each Frame's art library as a thumbnail grid."""

        name = "Samsung Frame Art"

        def __init__(self, hass: HomeAssistant) -> None:
            super().__init__(DOMAIN)
            self.hass = hass

        async def async_browse_media(
            self, item: MediaSourceItem
        ) -> BrowseMediaSource:
            art_clients = _art_entries(self.hass)

            # Level 2: a specific Frame's art grid.
            if item.identifier:
                entry_id = item.identifier.split("/", 1)[0]
                art = art_clients.get(entry_id)
                if art is None:
                    raise BrowseError(f"Unknown Frame: {entry_id}")
                artworks = await art.available(_ART_CATEGORY) or []
                children = [
                    build_art_child(
                        entry_id,
                        artwork["content_id"],
                        artwork.get("content_id", ""),
                    )
                    for artwork in artworks
                    if artwork.get("content_id")
                ]
                return BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=entry_id,
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.IMAGE,
                    title=_entry_title(self.hass, entry_id),
                    can_play=False,
                    can_expand=True,
                    children_media_class=MediaClass.IMAGE,
                    children=children,
                )

            # Level 1 (root): one directory per Frame.
            frames = [
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=entry_id,
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.IMAGE,
                    title=_entry_title(self.hass, entry_id),
                    can_play=False,
                    can_expand=True,
                )
                for entry_id in art_clients
            ]
            return BrowseMediaSource(
                domain=DOMAIN,
                identifier="",
                media_class=MediaClass.DIRECTORY,
                media_content_type=MediaType.IMAGE,
                title="Samsung Frame Art",
                can_play=False,
                can_expand=True,
                children_media_class=MediaClass.DIRECTORY,
                children=frames,
            )

        async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
            entry_id, _, content_id = item.identifier.partition("/")
            return PlayMedia(
                thumbnail_url(entry_id, content_id, _RESOLVE_W), "image/jpeg"
            )

    async def async_get_media_source(hass: HomeAssistant) -> SamsungArtMediaSource:
        """Set up the Samsung Frame Art media source."""
        return SamsungArtMediaSource(hass)
