"""Evidence-disciplined diagnostics for HistoMetPath model-v1.

All outputs are descriptive research diagnostics. They are not diagnoses,
calibrated confidence estimates, tumor masks, or accuracy measurements.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import math
from typing import Iterable

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter

SATURATION_HIGH = 0.95
SATURATION_EXTREME = 0.99
NEAR_THRESHOLD_MARGIN = 0.10

@dataclass(frozen=True)
class MorphologyMetrics:
    mean_brightness: float
    intensity_std: float
    tissue_fraction: float
    open_space_fraction: float
    edge_density: float
    texture_entropy: float
    nuclear_like_fraction: float
    red_mean: float
    green_mean: float
    blue_mean: float
    he_like_purple_fraction: float
    blur_proxy: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _entropy(gray: np.ndarray) -> float:
    hist = np.bincount(gray.reshape(-1), minlength=256).astype(float)
    p = hist / max(hist.sum(), 1.0)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def image_morphology_metrics(image: Image.Image) -> MorphologyMetrics:
    rgb = np.asarray(image.convert('RGB').resize((96, 96)), dtype=np.uint8)
    gray = np.asarray(image.convert('L').resize((96, 96)), dtype=np.uint8)
    mean = float(gray.mean())
    std = float(gray.std())
    tissue = float(np.mean(gray < 235))
    open_space = float(np.mean(gray >= 235))
    edges = np.asarray(Image.fromarray(gray).filter(ImageFilter.FIND_EDGES), dtype=np.uint8)
    edge_density = float(np.mean(edges > 32))
    # A deterministic descriptive proxy, not a cell detector.
    nuclear_like = float(np.mean((rgb[:, :, 2] > rgb[:, :, 0]) & (gray < 145)))
    purple = float(np.mean((rgb[:, :, 2] >= rgb[:, :, 1]) & (rgb[:, :, 0] >= rgb[:, :, 1]) & (gray < 210)))
    lap = np.asarray(Image.fromarray(gray).filter(ImageFilter.Kernel((3, 3), (0,1,0,1,-4,1,0,1,0), scale=1)), dtype=float)
    blur_proxy = float(np.var(lap))
    channels = rgb.reshape(-1, 3).mean(axis=0)
    return MorphologyMetrics(
        mean_brightness=mean,
        intensity_std=std,
        tissue_fraction=tissue,
        open_space_fraction=open_space,
        edge_density=edge_density,
        texture_entropy=_entropy(gray),
        nuclear_like_fraction=nuclear_like,
        red_mean=float(channels[0]),
        green_mean=float(channels[1]),
        blue_mean=float(channels[2]),
        he_like_purple_fraction=purple,
        blur_proxy=blur_proxy,
    )


def score_diagnostics(frame: pd.DataFrame, threshold: float = 0.5) -> dict[str, object]:
    scores = pd.to_numeric(frame.get('score', pd.Series(dtype=float)), errors='coerce').dropna()
    total = int(len(frame))
    valid = int(len(scores))
    if valid == 0:
        return {
            'total_records': total, 'valid_scores': 0, 'missing_scores': total,
            'fraction_at_least_0_95': None, 'fraction_at_least_0_99': None,
            'near_threshold_fraction': None, 'saturation_warning': False,
        }
    arr = scores.to_numpy(float)
    frac95 = float(np.mean(arr >= SATURATION_HIGH))
    frac99 = float(np.mean(arr >= SATURATION_EXTREME))
    near = float(np.mean(np.abs(arr - threshold) < NEAR_THRESHOLD_MARGIN))
    return {
        'total_records': total, 'valid_scores': valid, 'missing_scores': total - valid,
        'minimum_score': float(np.min(arr)), 'maximum_score': float(np.max(arr)),
        'mean_score': float(np.mean(arr)), 'median_score': float(np.median(arr)),
        'score_std': float(np.std(arr)), 'q25_score': float(np.quantile(arr, .25)),
        'q75_score': float(np.quantile(arr, .75)),
        'above_threshold_fraction': float(np.mean(arr >= threshold)),
        'fraction_at_least_0_95': frac95, 'fraction_at_least_0_99': frac99,
        'near_threshold_fraction': near,
        'saturation_warning': bool(frac99 >= 0.25 or frac95 >= 0.50),
    }


def duplicate_summary(frame: pd.DataFrame) -> dict[str, object]:
    if 'image_sha256' not in frame:
        return {'unique_hashes': 0, 'duplicate_records': 0, 'duplicate_groups': 0}
    hashes = frame['image_sha256'].dropna().astype(str)
    counts = hashes.value_counts()
    duplicated = counts[counts > 1]
    return {
        'unique_hashes': int(counts.size),
        'duplicate_records': int(duplicated.sum() - len(duplicated)),
        'duplicate_groups': int(len(duplicated)),
    }


def threshold_distance_band(score: float, threshold: float = 0.5) -> str:
    margin = abs(float(score) - threshold)
    if margin < 0.10:
        return 'near_threshold'
    if margin < 0.30:
        return 'intermediate_distance'
    return 'far_from_threshold'


def append_diagnostic_columns(frame: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    output = frame.copy()
    numeric = pd.to_numeric(output.get('score'), errors='coerce')
    output['threshold_distance'] = (numeric - threshold).abs()
    output['threshold_distance_band'] = numeric.map(
        lambda value: threshold_distance_band(value, threshold) if pd.notna(value) else 'not_scored'
    )
    output['score_at_least_0_95'] = numeric >= SATURATION_HIGH
    output['score_at_least_0_99'] = numeric >= SATURATION_EXTREME
    return output


def model_contract_receipt(*, expected_sha256: str, observed_sha256: str,
                           code_threshold: float, artifact_threshold: float,
                           architecture: str, input_size: Iterable[int]) -> dict[str, object]:
    threshold_match = math.isclose(float(code_threshold), float(artifact_threshold), rel_tol=0, abs_tol=1e-12)
    return {
        'expected_model_sha256': expected_sha256,
        'observed_model_sha256': observed_sha256,
        'model_hash_match': expected_sha256 == observed_sha256,
        'code_threshold': float(code_threshold),
        'artifact_threshold': float(artifact_threshold),
        'threshold_match': threshold_match,
        'architecture': architecture,
        'input_size': list(input_size),
        'contract_pass': bool(expected_sha256 == observed_sha256 and threshold_match and architecture == 'resnet18' and list(input_size) == [96, 96]),
    }
