import io
import pandas as pd
import pytest
from PIL import Image

from histometpath_web.regional_analysis import TileConfig, connected_components, decode_large_image, extract_tiles, spatial_coverage_summary


def image_bytes(size=(192, 192), color=(120, 80, 140)):
    image = Image.new("RGB", size, color); buffer = io.BytesIO(); image.save(buffer, format="PNG"); return buffer.getvalue()


def test_decode_and_nonoverlap_tiling():
    tiles = extract_tiles(decode_large_image(image_bytes()), TileConfig())
    assert len(tiles) == 4
    assert {(tile["x"], tile["y"]) for tile in tiles} == {(0, 0), (96, 0), (0, 96), (96, 96)}


def test_overlap_tiling():
    tiles = extract_tiles(decode_large_image(image_bytes()), TileConfig(stride=48))
    assert len(tiles) == 9


def test_small_image_rejected():
    with pytest.raises(ValueError, match="smaller"):
        extract_tiles(decode_large_image(image_bytes((64, 64))), TileConfig())


def test_tile_limit_guard():
    with pytest.raises(ValueError, match="1,000"):
        extract_tiles(Image.new("RGB", (5000, 5000), "white"), TileConfig(stride=48))


def test_coverage_nonoverlap():
    frame = pd.DataFrame({"included_in_inference": [True, True], "threshold_prediction": [1, 0], "stride": [96, 96]})
    result = spatial_coverage_summary(frame, 192, 96, 0.5)
    assert result["above_threshold_represented_pixels"] == 9216
    assert result["above_threshold_represented_area_um2"] == pytest.approx(2304)


def test_coverage_overlap_disables_area_sum():
    frame = pd.DataFrame({"included_in_inference": [True], "threshold_prediction": [1], "stride": [48]})
    assert spatial_coverage_summary(frame, 96, 96)["represented_image_pixels"] is None


def test_connected_components():
    frame = pd.DataFrame({"x": [0, 96, 300], "y": [0, 0, 300], "score": [0.9, 0.8, 0.7], "threshold_prediction": [1, 1, 1], "included_in_inference": [True, True, True]})
    clusters = connected_components(frame)
    assert sorted(clusters["tile_count"].tolist()) == [1, 2]
