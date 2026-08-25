from io import BytesIO
from pathlib import Path
import os

from PIL import Image
import pytest

from histometpath_web.inference import (
    EXPECTED_MODEL_SHA256,
    ImageValidationError,
    decode_uploaded_image,
    load_inference_model,
    predict_image,
)


def png_bytes(size=(96, 96), color=(120, 80, 160)):
    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format="PNG")
    return stream.getvalue()


def test_decode_png():
    image = decode_uploaded_image(png_bytes())
    assert image.size == (96, 96)
    assert image.format == "PNG"


def test_reject_empty_upload():
    with pytest.raises(ImageValidationError, match="empty"):
        decode_uploaded_image(b"")


def test_reject_non_image():
    with pytest.raises(ImageValidationError, match="not a readable"):
        decode_uploaded_image(b"not an image")


def test_validated_reference_scores_when_local_artifacts_available():
    model_path = os.environ.get("HISTOMETPATH_MODEL_PATH")
    positive_path = os.environ.get("HISTOMETPATH_POSITIVE_PNG")
    negative_path = os.environ.get("HISTOMETPATH_NEGATIVE_PNG")
    if not all((model_path, positive_path, negative_path)):
        pytest.skip("Local validated inference artifacts were not configured.")
    model, _ = load_inference_model(model_path)
    positive = predict_image(Image.open(Path(positive_path)), model)
    negative = predict_image(Image.open(Path(negative_path)), model)
    assert positive.model_sha256 == EXPECTED_MODEL_SHA256
    assert positive.score == pytest.approx(0.8856996297836304, abs=0.0)
    assert negative.score == pytest.approx(0.007876121439039707, abs=0.0)
    assert positive.threshold_prediction == 1
    assert negative.threshold_prediction == 0
