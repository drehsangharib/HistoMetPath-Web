from __future__ import annotations

from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest

from histometpath_web.model_acquisition import (
    ModelAcquisitionError,
    acquire_model,
    verify_model_file,
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


@contextmanager
def local_server(directory: Path):
    handler = partial(QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def disable_local_override(monkeypatch):
    monkeypatch.delenv("HISTOMETPATH_MODEL_PATH", raising=False)


def test_verified_local_override(validated_model_path):
    acquired = acquire_model(local_override=validated_model_path)
    assert acquired == validated_model_path
    assert verify_model_file(acquired) == acquired


def test_clean_cache_download_from_local_http(validated_model_path, tmp_path, monkeypatch):
    disable_local_override(monkeypatch)
    served = tmp_path / "served"
    served.mkdir()
    source = served / validated_model_path.name
    source.write_bytes(validated_model_path.read_bytes())
    cache = tmp_path / "clean-cache" / validated_model_path.name
    with local_server(served) as base:
        acquired = acquire_model(cache_path=cache, model_url=base + "/" + source.name)
    assert acquired == cache.resolve()
    assert acquired.read_bytes() == source.read_bytes()
    assert verify_model_file(acquired) == acquired


def test_corrupt_download_is_rejected_and_removed(validated_model_path, tmp_path, monkeypatch):
    disable_local_override(monkeypatch)
    served = tmp_path / "served"
    served.mkdir()
    bad = served / validated_model_path.name
    bad.write_bytes(b"corrupt")
    cache = tmp_path / "cache" / validated_model_path.name
    with local_server(served) as base:
        with pytest.raises(ModelAcquisitionError, match="size mismatch"):
            acquire_model(cache_path=cache, model_url=base + "/" + bad.name)
    assert not cache.exists()
    if cache.parent.exists():
        assert list(cache.parent.glob("*.part")) == []


def test_invalid_cached_file_is_replaced(validated_model_path, tmp_path, monkeypatch):
    disable_local_override(monkeypatch)
    served = tmp_path / "served"
    served.mkdir()
    source = served / validated_model_path.name
    source.write_bytes(validated_model_path.read_bytes())
    cache = tmp_path / "cache" / validated_model_path.name
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"invalid cache")
    with local_server(served) as base:
        acquired = acquire_model(cache_path=cache, model_url=base + "/" + source.name)
    assert acquired == cache.resolve()
    assert acquired.read_bytes() == source.read_bytes()
    assert verify_model_file(acquired) == acquired
