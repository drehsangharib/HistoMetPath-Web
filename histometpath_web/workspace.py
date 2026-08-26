"""Shared state and export utilities for connected patch analysis."""
from __future__ import annotations

import hashlib
import io
import json
import math
import zipfile
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd

SESSION_KEY = "histometpath_analysis_workspace"
RESULT_COLUMNS = [
    "filename", "score", "threshold_prediction", "threshold_interpretation",
    "width", "height", "original_mode", "image_sha256", "error",
]


def new_workspace() -> dict:
    return {"single_patch": None, "collection": [], "coordinates": None, "coordinate_source": None}


def ensure_workspace(session_state) -> dict:
    if SESSION_KEY not in session_state:
        session_state[SESSION_KEY] = new_workspace()
    return session_state[SESSION_KEY]


def clear_workspace(session_state) -> None:
    session_state[SESSION_KEY] = new_workspace()


def image_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collection_frame(records: Iterable[dict]) -> pd.DataFrame:
    rows = list(records)
    if not rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    frame = pd.DataFrame(rows)
    for column in RESULT_COLUMNS:
        if column not in frame:
            frame[column] = None
    return frame[RESULT_COLUMNS]


def collection_summary(frame: pd.DataFrame) -> dict:
    valid = frame[frame["error"].isna()].copy() if not frame.empty else frame.copy()
    scores = pd.to_numeric(valid["score"], errors="coerce").dropna()
    if scores.empty:
        return {"uploaded": len(frame), "analyzed": 0, "rejected": len(frame), "above": 0, "below": 0,
                "fraction_above": None, "mean": None, "median": None, "minimum": None, "maximum": None}
    above = int((scores >= 0.5).sum())
    return {"uploaded": len(frame), "analyzed": len(scores), "rejected": len(frame) - len(scores),
            "above": above, "below": len(scores) - above, "fraction_above": above / len(scores),
            "mean": float(scores.mean()), "median": float(scores.median()),
            "minimum": float(scores.min()), "maximum": float(scores.max())}


def duplicate_groups(frame: pd.DataFrame) -> list[list[str]]:
    valid = frame[frame["image_sha256"].notna()]
    return [group["filename"].tolist() for _, group in valid.groupby("image_sha256") if len(group) > 1]


def coordinate_template(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"filename": frame["filename"].tolist(), "x": [""] * len(frame), "y": [""] * len(frame)})


def generated_qa_grid(frame: pd.DataFrame, columns: int = 5, spacing: int = 96) -> pd.DataFrame:
    columns = max(1, int(columns)); spacing = max(1, int(spacing))
    rows = []
    for index, filename in enumerate(frame["filename"].tolist()):
        rows.append({"filename": filename, "x": (index % columns) * spacing,
                     "y": math.floor(index / columns) * spacing, "coordinate_source": "generated_qa_grid"})
    return pd.DataFrame(rows)


def validate_coordinate_frame(frame: pd.DataFrame, filenames: set[str]) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    required = {"filename", "x", "y"}
    missing = required - set(normalized.columns)
    if missing:
        detected = ", ".join(normalized.columns) or "none"
        raise ValueError(
            "This file is not a coordinate manifest. Required columns: filename, x, y. "
            f"Missing: {', '.join(sorted(missing))}. Detected: {detected}. "
            "Download a coordinate template or generated QA grid from Patch Collection Analysis."
        )
    result = normalized[["filename", "x", "y"]].copy()
    result["filename"] = result["filename"].astype(str).str.strip()
    if result["filename"].duplicated().any():
        raise ValueError("Coordinate CSV contains duplicate filenames.")
    result["x"] = pd.to_numeric(result["x"], errors="raise")
    result["y"] = pd.to_numeric(result["y"], errors="raise")
    unknown = sorted(set(result["filename"]) - filenames)
    missing_rows = sorted(filenames - set(result["filename"]))
    if unknown:
        raise ValueError("Coordinate CSV references files outside the current collection: " + ", ".join(unknown[:5]))
    if missing_rows:
        raise ValueError("Coordinate CSV is missing current collection files: " + ", ".join(missing_rows[:5]))
    if result.duplicated(["x", "y"]).any():
        raise ValueError("Coordinate CSV contains duplicate x/y positions.")
    return result


def build_session_bundle(frame: pd.DataFrame, coordinates: pd.DataFrame | None, coordinate_source: str | None,
                         model_sha256: str, application_commit: str) -> bytes:
    summary = collection_summary(frame)
    receipt = {
        "schema_version": "1.0", "created_utc": datetime.now(timezone.utc).isoformat(),
        "application_commit": application_commit, "model_sha256": model_sha256,
        "historical_threshold": 0.5, "threshold_modified": False,
        "analysis_level": "patch_collection", "collection_summary": summary,
        "coordinate_source": coordinate_source, "clinical_use": False,
        "external_execution_consumed": False,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("patch_inference_results.csv", frame.to_csv(index=False))
        archive.writestr("patch_inference_results.json", json.dumps(frame.to_dict(orient="records"), indent=2))
        archive.writestr("coordinate_template.csv", coordinate_template(frame).to_csv(index=False))
        archive.writestr("generated_qa_grid.csv", generated_qa_grid(frame).to_csv(index=False))
        if coordinates is not None:
            archive.writestr("connected_coordinates.csv", coordinates.to_csv(index=False))
        archive.writestr("analysis_receipt.json", json.dumps(receipt, indent=2))
        archive.writestr("README.txt", "Research-only patch analysis. Generated QA coordinates are not original tissue geometry.\n")
    return buffer.getvalue()
