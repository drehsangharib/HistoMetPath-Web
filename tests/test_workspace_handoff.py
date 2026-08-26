import io
import zipfile

import pandas as pd
import pytest

from histometpath_web.workspace import (build_session_bundle, coordinate_template, duplicate_groups,
    generated_qa_grid, validate_coordinate_frame)


def frame():
    return pd.DataFrame([
        {"filename": "a.png", "score": 0.1, "threshold_prediction": 0, "threshold_interpretation": "below", "width": 96, "height": 96, "original_mode": "RGB", "image_sha256": "same", "error": None},
        {"filename": "b.png", "score": 0.9, "threshold_prediction": 1, "threshold_interpretation": "above", "width": 96, "height": 96, "original_mode": "RGB", "image_sha256": "same", "error": None},
    ])


def test_coordinate_template_has_required_columns():
    result = coordinate_template(frame())
    assert list(result.columns) == ["filename", "x", "y"]


def test_generated_grid():
    result = generated_qa_grid(frame(), columns=1, spacing=96)
    assert result[["x", "y"]].values.tolist() == [[0, 0], [0, 96]]


def test_results_csv_error_is_actionable():
    with pytest.raises(ValueError, match="Detected: filename, score"):
        validate_coordinate_frame(pd.DataFrame({"filename": ["a.png"], "score": [0.1]}), {"a.png"})


def test_duplicate_detection():
    assert duplicate_groups(frame()) == [["a.png", "b.png"]]


def test_session_bundle_contains_expected_files():
    payload = build_session_bundle(frame(), None, None, "hash", "commit")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
    assert {"patch_inference_results.csv", "coordinate_template.csv", "generated_qa_grid.csv", "analysis_receipt.json"} <= names
