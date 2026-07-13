"""media_source: browse the art library as a thumbnail grid (no base64).

The thumbnails are served by the integration's existing HTTP view
(``/api/samsungtv_smart/thumbnail``), which resolves ``?path=`` to a real file
under ``<config>/www``. The frame_art coordinator materializes a per-artwork
JPEG at ``www/frame_art/<entry_id>/<subdir>/<content_id>.jpg`` (subdir =
personal/store/other), so the browsable grid points each tile at that on-disk
copy through the view. No base64 anywhere.
"""
import sys
from pathlib import Path

import pytest

COMP = Path(__file__).resolve().parents[1] / "custom_components" / "samsungtv_smart"
sys.path.insert(0, str(COMP))


def test_domain_matches_integration():
    import media_source as ms

    assert ms.DOMAIN == "samsungtv_smart"


def test_subdir_classification_mirrors_coordinator():
    # Must match sensor.py's thumbnail-writer exactly, or the URL points at a
    # file that isn't there. MY_F* -> personal, SAM-* -> store, else -> other.
    import media_source as ms

    assert ms._subdir_for_content("MY_F0001") == "personal"
    assert ms._subdir_for_content("SAM-F0042") == "store"
    assert ms._subdir_for_content("SAM-S0007") == "store"
    assert ms._subdir_for_content("weird-id") == "other"


def test_thumbnail_url_uses_http_view_www_path():
    import media_source as ms

    url = ms.thumbnail_url("abc123", "MY_F0001", width=200)
    assert url == (
        "/api/samsungtv_smart/thumbnail"
        "?path=/local/frame_art/abc123/personal/MY_F0001.jpg&w=200"
    )
    assert "base64" not in url


def test_thumbnail_url_sanitizes_colon_in_content_id():
    import media_source as ms

    url = ms.thumbnail_url("e1", "SAM-S1:2", width=128)
    assert "/store/SAM-S1_2.jpg" in url
    assert "w=128" in url


def test_build_art_child_carries_thumbnail_and_domain():
    # Constructing a real BrowseMediaSource needs Home Assistant installed.
    pytest.importorskip("homeassistant.components.media_source")
    import media_source as ms

    child = ms.build_art_child("abc123", "MY_F0001", "Sunset")
    assert child.domain == ms.DOMAIN
    assert child.identifier == "abc123/MY_F0001"
    assert child.thumbnail == (
        "/api/samsungtv_smart/thumbnail"
        "?path=/local/frame_art/abc123/personal/MY_F0001.jpg&w=200"
    )
    assert child.can_play is True
    assert child.can_expand is False
