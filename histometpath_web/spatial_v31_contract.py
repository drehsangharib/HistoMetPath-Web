"""Safe browser-to-worker contract for Spatial-v3.1 WSI research workflows.

The web application does not open or upload whole-slide images. It creates a
small job specification for an authorized local/worker execution and validates
returned research receipts without trusting filenames or server paths.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import PurePath
from typing import Any
import zipfile

SCHEMA_VERSION = "1.0"
SAMPLER_NAME = "Spatial-v3.1"
MAX_RECEIPT_BUNDLE_BYTES = 10 * 1024 * 1024
MAX_ZIP_MEMBERS = 100
MAX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
REQUIRED_RESULT_RECEIPT = "SPATIAL_V31_MEGA2_FIX2A_QUALIFICATION_RECEIPT.json"

class SpatialV31ContractError(ValueError):
    """Raised when a WSI job or returned receipt violates the safe contract."""

@dataclass(frozen=True)
class SpatialV31Job:
    slide_id: str
    source_locator: str
    expected_label: str
    coordinate_count: int = 300
    development_only: bool = True
    clinical_use: bool = False
    validation_access_authorized: bool = False
    protected_test_access_authorized: bool = False
    camelyon17_access_authorized: bool = False
    annotation_access_authorized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "sampler": SAMPLER_NAME, **asdict(self)}


def _safe_token(value: str, field: str) -> str:
    text = str(value).strip()
    if not text or len(text) > 128:
        raise SpatialV31ContractError(f"{field} must contain 1 to 128 characters.")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if any(char not in allowed for char in text) or text in {".", ".."}:
        raise SpatialV31ContractError(f"{field} contains unsupported characters.")
    return text


def create_job_spec(slide_id: str, source_locator: str, expected_label: str) -> dict[str, Any]:
    slide = _safe_token(slide_id, "slide_id")
    locator = str(source_locator).strip()
    if not locator or len(locator) > 512:
        raise SpatialV31ContractError("source_locator must contain 1 to 512 characters.")
    if locator.startswith(("http://", "https://")):
        raise SpatialV31ContractError("Remote WSI URLs are not accepted by this contract.")
    label = expected_label.strip().lower()
    if label not in {"normal", "tumor", "unknown"}:
        raise SpatialV31ContractError("expected_label must be normal, tumor, or unknown.")
    return SpatialV31Job(slide, locator, label).to_dict()


def job_spec_bytes(spec: dict[str, Any]) -> bytes:
    validate_job_spec(spec)
    return (json.dumps(spec, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validate_job_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if spec.get("schema_version") != SCHEMA_VERSION or spec.get("sampler") != SAMPLER_NAME:
        raise SpatialV31ContractError("Unexpected job schema or sampler.")
    _safe_token(spec.get("slide_id", ""), "slide_id")
    if spec.get("coordinate_count") != 300:
        raise SpatialV31ContractError("Spatial-v3.1 jobs require exactly 300 coordinates.")
    if spec.get("development_only") is not True or spec.get("clinical_use") is not False:
        raise SpatialV31ContractError("Research-only job boundaries are required.")
    prohibited = ("validation_access_authorized", "protected_test_access_authorized", "camelyon17_access_authorized", "annotation_access_authorized")
    if any(spec.get(key) is not False for key in prohibited):
        raise SpatialV31ContractError("Protected or annotation access cannot be authorized here.")
    return spec


def _safe_zip_name(name: str) -> bool:
    path = PurePath(name.replace("\\", "/"))
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def validate_result_bundle(data: bytes) -> dict[str, Any]:
    if not data:
        raise SpatialV31ContractError("Result bundle is empty.")
    if len(data) > MAX_RECEIPT_BUNDLE_BYTES:
        raise SpatialV31ContractError("Result bundle exceeds the 10 MB browser validation limit.")
    try:
        archive = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile as error:
        raise SpatialV31ContractError("Result bundle is not a readable ZIP archive.") from error
    with archive:
        members = archive.infolist()
        if not 1 <= len(members) <= MAX_ZIP_MEMBERS:
            raise SpatialV31ContractError("Unexpected ZIP member count.")
        if any(not _safe_zip_name(info.filename) for info in members):
            raise SpatialV31ContractError("Unsafe ZIP member path detected.")
        total = sum(info.file_size for info in members)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise SpatialV31ContractError("Uncompressed result bundle exceeds the safety limit.")
        receipt_matches = [info for info in members if PurePath(info.filename).name == REQUIRED_RESULT_RECEIPT]
        if len(receipt_matches) != 1:
            raise SpatialV31ContractError("Expected exactly one Spatial-v3.1 qualification receipt.")
        try:
            receipt = json.loads(archive.read(receipt_matches[0]).decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SpatialV31ContractError("Qualification receipt is not valid UTF-8 JSON.") from error
    required_true = ("coordinates_byte_reproducible", "fractions_byte_reproducible", "restart_reuse_validated", "corrupt_copy_rejected", "passed")
    if any(receipt.get(key) is not True for key in required_true):
        raise SpatialV31ContractError("Qualification receipt does not pass all required gates.")
    required_zero = ("restart_wsi_files_opened", "restart_region_reads", "saved_tile_pixels", "validation_arrays_opened", "protected_test_arrays_opened", "camelyon17_files_opened", "annotations_opened", "training_operations", "evaluation_operations")
    if any(receipt.get(key) != 0 for key in required_zero):
        raise SpatialV31ContractError("Qualification receipt violates a zero-access boundary.")
    if receipt.get("run1_selected_coordinate_count") != 300 or receipt.get("run2_selected_coordinate_count") != 300:
        raise SpatialV31ContractError("Qualification receipt must report 300 coordinates per run.")
    return {
        "bundle_sha256": sha256(data).hexdigest(),
        "bundle_size_bytes": len(data),
        "receipt": receipt,
        "contract_pass": True,
        "clinical_use": False,
    }
