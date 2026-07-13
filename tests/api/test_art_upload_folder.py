"""upload_folder: scan a server-side folder, dedup via an in-folder sidecar.

Backs the ``art_upload_folder`` HA service. Run 1 uploads every image; run 2
of the unchanged folder uploads 0 (sidecar skip), which is the whole point of
the dedup feature being usable from HA.
"""
import asyncio
import json
import os

import pytest


async def test_upload_folder_uploads_images_and_writes_sidecar(
    art_client, tmp_path, monkeypatch
):
    async def no_sleep(_secs):
        return None

    calls: list[str] = []

    async def fake_upload(file, *a, **k):
        calls.append(file)
        return "CID-" + os.path.basename(file)

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)

    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "b.png").write_bytes(b"b")
    (tmp_path / "notes.txt").write_bytes(b"skip me")  # non-image ignored

    result = await art_client.upload_folder(str(tmp_path))

    # Only the two images were uploaded; the .txt was ignored.
    assert sorted(os.path.basename(c) for c in calls) == ["a.jpg", "b.png"]
    assert result == ["CID-a.jpg", "CID-b.png"]

    # Sidecar was written inside the folder and records both images.
    sidecar = tmp_path / ".dedup_sidecar.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert set(data) == {"a.jpg", "b.png"}


async def test_upload_folder_second_run_uploads_zero(
    art_client, tmp_path, monkeypatch
):
    async def no_sleep(_secs):
        return None

    calls: list[str] = []

    async def fake_upload(file, *a, **k):
        calls.append(file)
        return "CID-" + os.path.basename(file)

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)

    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "b.jpg").write_bytes(b"b")

    first = await art_client.upload_folder(str(tmp_path))
    assert len(first) == 2
    assert len(calls) == 2

    calls.clear()
    second = await art_client.upload_folder(str(tmp_path))
    assert second == []   # unchanged folder -> dedup skip
    assert calls == []    # 0 uploads on run 2


async def test_upload_folder_uses_in_folder_sidecar_path(
    art_client, tmp_path, monkeypatch
):
    """The service must dedup against a sidecar living in the target folder."""
    captured = {}

    async def fake_batch(files, hass=None, throttle=None, sidecar_path=None):
        captured["files"] = files
        captured["sidecar_path"] = sidecar_path
        return []

    monkeypatch.setattr(art_client, "upload_batch", fake_batch)
    (tmp_path / "x.jpg").write_bytes(b"x")

    await art_client.upload_folder(str(tmp_path))

    assert captured["sidecar_path"] == os.path.join(str(tmp_path), ".dedup_sidecar.json")
    assert captured["files"] == [os.path.join(str(tmp_path), "x.jpg")]


async def test_upload_folder_missing_dir_raises(art_client):
    with pytest.raises(FileNotFoundError):
        await art_client.upload_folder("/no/such/folder/here")
