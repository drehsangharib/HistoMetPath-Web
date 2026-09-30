"""Large-image tiling, quality control, spatial summaries, and safe exports."""
from __future__ import annotations

import hashlib
import io
import math
from collections import deque
from dataclasses import dataclass

import numpy as np
import pandas as pd
from PIL import Image, ImageStat

TILE_SIZE = 96
MAX_DECODED_PIXELS = 40_000_000
MAX_BASE_DECODED_BYTES = 160 * 1024 * 1024
MAX_TILES = 1_000


@dataclass(frozen=True)
class TileConfig:
    tile_size: int = TILE_SIZE
    stride: int = TILE_SIZE
    include_partial: bool = False
    blank_brightness: float = 245.0
    minimum_intensity_std: float = 5.0


def inspect_large_image(data: bytes) -> dict:
    """Inspect image headers and enforce resource limits before full decoding."""
    if not data:
        raise ValueError("Uploaded image is empty.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            image_format = image.format
            mode = image.mode
    except Exception as error:
        raise ValueError(f"Could not inspect image header: {error}") from error

    pixels = int(width) * int(height)
    megapixels = pixels / 1_000_000
    estimated_rgb_bytes = pixels * 3
    info = {
        "width": int(width),
        "height": int(height),
        "pixels": pixels,
        "megapixels": megapixels,
        "compressed_bytes": len(data),
        "estimated_rgb_bytes": estimated_rgb_bytes,
        "format": image_format,
        "mode": mode,
    }
    if pixels > MAX_DECODED_PIXELS:
        raise ValueError(
            f"This image is {megapixels:.1f} megapixels ({width:,} x {height:,}), "
            f"exceeding the deployed {MAX_DECODED_PIXELS / 1_000_000:.1f}-megapixel "
            "safety limit. The compressed file may be below 25 MB while decoded "
            "memory is much larger. Resize or crop the image, or use the controlled "
            "local workflow."
        )
    if estimated_rgb_bytes > MAX_BASE_DECODED_BYTES:
        raise ValueError(
            f"The estimated base RGB footprint is {estimated_rgb_bytes / 1048576:.1f} MB, "
            f"exceeding the deployed {MAX_BASE_DECODED_BYTES / 1048576:.0f} MB "
            "memory-safety limit. Resize or crop the image, or use the controlled "
            "local workflow."
        )
    return info


def decode_large_image(data: bytes) -> Image.Image:
    inspect_large_image(data)
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as error:
        raise ValueError(f"Could not decode image: {error}") from error
    return image.convert("RGB")


def _positions(length: int, tile_size: int, stride: int, include_partial: bool) -> list[int]:
    if length < tile_size:
        return [0] if include_partial else []
    positions = list(range(0, length - tile_size + 1, stride))
    if include_partial and positions[-1] != length - tile_size:
        positions.append(length - tile_size)
    return positions


def tile_quality(image: Image.Image, config: TileConfig) -> dict:
    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    mean = float(stat.mean[0]); std = float(stat.stddev[0])
    blank_like = mean >= config.blank_brightness or std < config.minimum_intensity_std
    return {"mean_brightness": mean, "intensity_std": std, "blank_like": blank_like}


def extract_tiles(image: Image.Image, config: TileConfig) -> list[dict]:
    if config.tile_size != TILE_SIZE:
        raise ValueError("The frozen model requires 96 x 96 tiles.")
    if not 1 <= config.stride <= config.tile_size:
        raise ValueError("Stride must be between 1 and 96 pixels.")
    xs = _positions(image.width, config.tile_size, config.stride, config.include_partial)
    ys = _positions(image.height, config.tile_size, config.stride, config.include_partial)
    if not xs or not ys:
        raise ValueError("Image is smaller than 96 x 96. Use Single-Patch Analysis instead.")
    if len(xs) * len(ys) > MAX_TILES:
        raise ValueError(f"Requested tiling would create more than {MAX_TILES:,} tiles.")
    rows = []
    for row, y in enumerate(ys):
        for column, x in enumerate(xs):
            tile = image.crop((x, y, x + config.tile_size, y + config.tile_size))
            buffer = io.BytesIO(); tile.save(buffer, format="PNG"); payload = buffer.getvalue()
            quality = tile_quality(tile, config)
            rows.append({
                "tile_id": f"tile_r{row:04d}_c{column:04d}", "filename": f"tile_r{row:04d}_c{column:04d}.png",
                "x": x, "y": y, "row": row, "column": column, "width": config.tile_size,
                "height": config.tile_size, "bytes": payload, "image_sha256": hashlib.sha256(payload).hexdigest(),
                **quality,
            })
    return rows


def connected_components(frame: pd.DataFrame, tile_size: int = TILE_SIZE) -> pd.DataFrame:
    active = frame[(frame["threshold_prediction"] == 1) & frame["included_in_inference"]].copy()
    if active.empty:
        return pd.DataFrame(columns=["cluster_id", "tile_count", "min_x", "max_x", "min_y", "max_y", "mean_score", "max_score"])
    by_position = {(int(row.x), int(row.y)): row for row in active.itertuples()}
    visited, clusters = set(), []
    for start in by_position:
        if start in visited:
            continue
        queue = deque([start]); visited.add(start); members = []
        while queue:
            point = queue.popleft(); members.append(by_position[point])
            x, y = point
            for neighbor in ((x - tile_size, y), (x + tile_size, y), (x, y - tile_size), (x, y + tile_size)):
                if neighbor in by_position and neighbor not in visited:
                    visited.add(neighbor); queue.append(neighbor)
        scores = [float(member.score) for member in members]
        clusters.append({"cluster_id": len(clusters) + 1, "tile_count": len(members),
                         "min_x": min(member.x for member in members), "max_x": max(member.x for member in members) + tile_size,
                         "min_y": min(member.y for member in members), "max_y": max(member.y for member in members) + tile_size,
                         "mean_score": float(np.mean(scores)), "max_score": float(np.max(scores))})
    return pd.DataFrame(clusters).sort_values("tile_count", ascending=False).reset_index(drop=True)


def spatial_coverage_summary(frame: pd.DataFrame, image_width: int, image_height: int, mpp: float | None = None) -> dict:
    included = frame[frame["included_in_inference"]]
    above = included[included["threshold_prediction"] == 1]
    tile_area = TILE_SIZE * TILE_SIZE
    non_overlapping = bool((frame["stride"] == TILE_SIZE).all()) if not frame.empty and "stride" in frame else False
    represented_pixels = int(len(included) * tile_area) if non_overlapping else None
    above_pixels = int(len(above) * tile_area) if non_overlapping else None
    result = {
        "image_width": image_width, "image_height": image_height, "image_pixels": image_width * image_height,
        "extracted_tiles": len(frame), "analyzed_tiles": len(included), "excluded_blank_like_tiles": int((~frame["included_in_inference"]).sum()),
        "above_threshold_tiles": len(above), "above_threshold_tile_fraction": float(len(above) / len(included)) if len(included) else None,
        "non_overlapping_tiles": non_overlapping, "represented_image_pixels": represented_pixels,
        "above_threshold_represented_pixels": above_pixels,
    }
    if mpp is not None and mpp > 0 and non_overlapping:
        result["represented_area_um2"] = represented_pixels * mpp * mpp
        result["above_threshold_represented_area_um2"] = above_pixels * mpp * mpp
    return result


def overlay_png(image: Image.Image, frame: pd.DataFrame, alpha: int = 95) -> bytes:
    base = image.convert("RGBA"); layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(layer)
    for row in frame.itertuples():
        if not row.included_in_inference or pd.isna(row.score):
            color = (128, 128, 128, alpha)
        else:
            value = float(row.score); color = (int(255 * value), int(80 * (1 - value)), int(255 * (1 - value)), alpha)
        draw.rectangle((int(row.x), int(row.y), int(row.x) + TILE_SIZE, int(row.y) + TILE_SIZE), fill=color, outline=(255, 255, 255, 180))
    output = Image.alpha_composite(base, layer).convert("RGB")
    buffer = io.BytesIO(); output.save(buffer, format="PNG"); return buffer.getvalue()
