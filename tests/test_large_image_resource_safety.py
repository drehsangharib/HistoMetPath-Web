from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from histometpath_web.regional_analysis import decode_large_image, inspect_large_image


def _jpeg_bytes(width: int = 4, height: int = 3) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 80, 160)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _patch_jpeg_dimensions(data: bytes, width: int, height: int) -> bytes:
    payload = bytearray(data)
    for marker in (b"\xff\xc0", b"\xff\xc1", b"\xff\xc2"):
        index = payload.find(marker)
        if index >= 0:
            payload[index + 5:index + 7] = int(height).to_bytes(2, "big")
            payload[index + 7:index + 9] = int(width).to_bytes(2, "big")
            return bytes(payload)
    raise AssertionError("JPEG start-of-frame marker not found")


def test_safe_image_preflight_and_decode():
    data = _jpeg_bytes()
    info = inspect_large_image(data)
    assert info["width"] == 4
    assert info["height"] == 3
    assert info["pixels"] == 12
    assert info["estimated_rgb_bytes"] == 36
    decoded = decode_large_image(data)
    assert decoded.mode == "RGB"
    assert decoded.size == (4, 3)


def test_problem_image_rejected_from_header_before_full_decode(monkeypatch):
    data = _patch_jpeg_dimensions(_jpeg_bytes(), 8511, 8068)

    def fail_load(*args, **kwargs):
        raise AssertionError("full image decoding must not occur")

    monkeypatch.setattr(Image.Image, "load", fail_load)
    with pytest.raises(ValueError, match=r"68\.7 megapixels.*40\.0-megapixel"):
        decode_large_image(data)


def test_problem_image_message_explains_compressed_vs_decoded_size():
    data = _patch_jpeg_dimensions(_jpeg_bytes(), 8511, 8068)
    with pytest.raises(ValueError) as error:
        inspect_large_image(data)
    message = str(error.value)
    assert "below 25 MB" in message
    assert "Resize or crop" in message
    assert "controlled local workflow" in message


def test_analyze_page_uses_preflight_before_decode():
    source = (Path(__file__).resolve().parents[1] / "pages" / "2_Analyze.py").read_text(encoding="utf-8")
    assert "inspect_large_image" in source
    assert source.index("large_image_preflight = inspect_large_image(data)") < source.index(
        "preview_image = decode_large_image(data)"
    )
