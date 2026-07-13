"""Shared fixtures for Samsung Art client tests."""
import sys
from pathlib import Path

import pytest

# Make the vendored art client importable as a bare module.
API_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "samsungtv_smart" / "api"
sys.path.insert(0, str(API_DIR))


@pytest.fixture
def art_client():
    """A SamsungTVAsyncArt instance that never opens a real socket."""
    import art  # noqa: PLC0415

    client = art.SamsungTVAsyncArt(host="192.0.2.10", port=8002, token="tok", name="pytest")
    return client
