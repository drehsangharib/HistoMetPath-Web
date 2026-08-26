import pandas as pd
import pytest
from histometpath_web.workspace import collection_frame, collection_summary, image_sha256, new_workspace, validate_coordinate_frame


def test_new_workspace_is_empty():
    assert new_workspace() == {"single_patch": None, "collection": [], "coordinates": None, "coordinate_source": None}


def test_collection_summary():
    frame = collection_frame([
        {"filename": "a.png", "score": 0.9, "threshold_prediction": 1, "error": None},
        {"filename": "b.png", "score": 0.1, "threshold_prediction": 0, "error": None},
        {"filename": "bad.png", "score": None, "threshold_prediction": None, "error": "bad"},
    ])
    summary = collection_summary(frame)
    assert summary["uploaded"] == 3
    assert summary["analyzed"] == 2
    assert summary["above"] == 1
    assert summary["fraction_above"] == pytest.approx(0.5)


def test_coordinate_validation():
    source = pd.DataFrame({"filename": ["a.png"], "x": [10], "y": [20]})
    result = validate_coordinate_frame(source, {"a.png"})
    assert result.iloc[0]["x"] == 10


def test_coordinate_validation_rejects_unknown():
    source = pd.DataFrame({"filename": ["other.png"], "x": [10], "y": [20]})
    with pytest.raises(ValueError, match="outside"):
        validate_coordinate_frame(source, {"a.png"})


def test_image_sha256_is_deterministic():
    assert image_sha256(b"abc") == image_sha256(b"abc")
