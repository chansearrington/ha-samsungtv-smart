"""Sidecar write must be NON-FATAL.

If the images already uploaded to the TV but persisting the dedup sidecar
fails (disk full, permissions, etc.), we must NOT drop the already-uploaded
content_ids on the floor. The upload path should log a warning and still
return the content_ids that made it onto the TV.
"""
import asyncio
import logging
import os

import _dedup


async def test_upload_batch_returns_ids_when_sidecar_write_fails(
    art_client, tmp_path, monkeypatch, caplog
):
    async def no_sleep(_secs):
        return None

    async def fake_upload(file, *a, **k):
        return "CID-" + os.path.basename(file)

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)
    monkeypatch.setattr(_dedup, "save_sidecar", boom)

    (tmp_path / "a.jpg").write_bytes(b"a")
    (tmp_path / "b.jpg").write_bytes(b"b")
    sidecar_path = str(tmp_path / ".dedup_sidecar.json")

    with caplog.at_level(logging.WARNING):
        result = await art_client.upload_batch(
            [str(tmp_path / "a.jpg"), str(tmp_path / "b.jpg")],
            sidecar_path=sidecar_path,
        )

    # Images are on the TV -> their content_ids must survive the write failure.
    assert result == ["CID-a.jpg", "CID-b.jpg"]
    assert any("sidecar" in r.getMessage().lower() for r in caplog.records)


async def test_upload_folder_returns_ids_when_sidecar_write_fails(
    art_client, tmp_path, monkeypatch, caplog
):
    async def no_sleep(_secs):
        return None

    async def fake_upload(file, *a, **k):
        return "CID-" + os.path.basename(file)

    def boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(art_client, "upload", fake_upload)
    monkeypatch.setattr(_dedup, "save_sidecar", boom)

    (tmp_path / "a.jpg").write_bytes(b"a")

    with caplog.at_level(logging.WARNING):
        result = await art_client.upload_folder(str(tmp_path))

    assert result == ["CID-a.jpg"]
    assert any("sidecar" in r.getMessage().lower() for r in caplog.records)
