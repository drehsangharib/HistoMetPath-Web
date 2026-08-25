"""Validated patch-level inference utilities for HistoMetPath-Web."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image, UnidentifiedImageError
import torch
from torch import nn
from torchvision import models, transforms

EXPECTED_MODEL_SHA256 = "d01611d5e370ad14cb4eb052ff1de31b6650780647f64107487a22eceba5cf90"
HISTORICAL_THRESHOLD = 0.5
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 4096 * 4096
NORMALIZATION_MEAN = [0.485, 0.456, 0.406]
NORMALIZATION_STD = [0.229, 0.224, 0.225]


class ImageValidationError(ValueError):
    """Raised when an uploaded image fails the inference input contract."""


class PatchClassifier(nn.Module):
    """ResNet-18 patch classifier matching the frozen scientific model."""

    def __init__(self) -> None:
        super().__init__()
        self.backbone = models.resnet18(weights=None)
        self.backbone.fc = nn.Identity()
        self.classifier = nn.Sequential(
            nn.Linear(512, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(512, 1),
        )

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.backbone(image))


@dataclass(frozen=True)
class InferenceResult:
    score: float
    historical_threshold: float
    threshold_prediction: int
    threshold_interpretation: str
    width: int
    height: int
    original_mode: str
    model_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_uploaded_image(upload: bytes | bytearray | BinaryIO) -> Image.Image:
    data = upload.read() if hasattr(upload, "read") else bytes(upload)
    if not data:
        raise ImageValidationError("The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageValidationError("The uploaded file exceeds the 10 MB limit.")
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ImageValidationError("The uploaded file is not a readable PNG or JPEG image.") from error
    if image.format not in {"PNG", "JPEG"}:
        raise ImageValidationError("Only decoded PNG and JPEG images are supported.")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ImageValidationError("The image dimensions are invalid.")
    if width * height > MAX_IMAGE_PIXELS:
        raise ImageValidationError("The image exceeds the 16.8-megapixel safety limit.")
    return image


def build_transform() -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize((96, 96)),
        transforms.ToTensor(),
        transforms.Normalize(mean=NORMALIZATION_MEAN, std=NORMALIZATION_STD),
    ])


def load_inference_model(model_path: str | Path) -> tuple[PatchClassifier, dict[str, object]]:
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Inference artifact not found: {path}")
    actual_hash = file_sha256(path)
    if actual_hash != EXPECTED_MODEL_SHA256:
        raise RuntimeError("Inference artifact SHA-256 does not match the validated model.")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    required = {"state_dict", "architecture", "input_size", "historical_threshold"}
    missing = sorted(required - set(payload))
    if missing:
        raise RuntimeError(f"Inference artifact is missing metadata: {', '.join(missing)}")
    if payload["architecture"] != "resnet18" or list(payload["input_size"]) != [96, 96]:
        raise RuntimeError("Inference artifact architecture or input contract is invalid.")
    model = PatchClassifier()
    model.load_state_dict(payload["state_dict"], strict=True)
    model.eval()
    return model, payload


def predict_image(image: Image.Image, model: PatchClassifier, model_sha256: str = EXPECTED_MODEL_SHA256) -> InferenceResult:
    original_mode = image.mode
    width, height = image.size
    rgb_image = image.convert("RGB")
    tensor = build_transform()(rgb_image).unsqueeze(0)
    with torch.inference_mode():
        logit = model(tensor).reshape(-1)[0]
        score = float(torch.sigmoid(logit).item())
    prediction = int(score >= HISTORICAL_THRESHOLD)
    return InferenceResult(
        score=score,
        historical_threshold=HISTORICAL_THRESHOLD,
        threshold_prediction=prediction,
        threshold_interpretation=(
            "Above the historical tumor-positive threshold"
            if prediction == 1
            else "Below the historical tumor-positive threshold"
        ),
        width=width,
        height=height,
        original_mode=original_mode,
        model_sha256=model_sha256,
    )
