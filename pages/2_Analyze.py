from pathlib import Path
import hashlib

import pandas as pd
import streamlit as st

from histometpath_web.inference import decode_uploaded_image, load_inference_model, predict_image
from histometpath_web.model_acquisition import acquire_model
from histometpath_web.regional_analysis import (
    TileConfig,
    decode_large_image,
    extract_tiles,
    spatial_coverage_summary,
    inspect_large_image,
)
from histometpath_web.workspace import collection_frame, ensure_workspace, generated_qa_grid, image_sha256
from histometpath_web.ui import configure, footer

configure("Analyze")
st.title("Analyze Images")
st.caption("Upload once, analyze once, then inspect distinct results pages")
workspace = ensure_workspace(st.session_state)
workspace.setdefault("regional", None)
mode = st.radio("Analysis input", ["Single patch", "Patch collection", "Large image"], horizontal=True)

@st.cache_resource
def model():
    local = Path(__file__).resolve().parents[1] / "local_model_artifacts" / "histometpath_resnet18_patch_state_dict.pt"
    path = acquire_model(local_override=local if local.is_file() else None)
    return load_inference_model(path)[0]

if mode == "Single patch":
    upload = st.file_uploader("Upload PNG or JPEG", type=["png", "jpg", "jpeg"], key="single")
    if upload and st.button("Analyze single patch", type="primary"):
        data = upload.getvalue(); image = decode_uploaded_image(data); result = predict_image(image, model()).to_dict()
        workspace["single_patch"] = {"filename": upload.name, "bytes": data, "image_sha256": image_sha256(data), "result": result}
        st.success("Single-patch analysis is ready in Results Overview and Analysis Record.")

elif mode == "Patch collection":
    uploads = st.file_uploader("Upload 2 to 100 PNG/JPEG patches", type=["png", "jpg", "jpeg"], accept_multiple_files=True, key="collection")
    if uploads and st.button("Analyze patch collection", type="primary"):
        if not 2 <= len(uploads) <= 100:
            st.error("Upload between 2 and 100 patches.")
        else:
            records, bar = [], st.progress(0)
            for index, upload in enumerate(uploads, start=1):
                data = upload.getvalue(); base = {"filename": upload.name, "image_sha256": image_sha256(data), "error": None}
                try:
                    result = predict_image(decode_uploaded_image(data), model()).to_dict(); records.append({**base, **result})
                except Exception as error:
                    records.append({**base, "score": None, "threshold_prediction": None, "threshold_interpretation": None,
                                    "width": None, "height": None, "original_mode": None, "error": str(error)})
                bar.progress(index / len(uploads))
            workspace["collection"] = records
            grid = generated_qa_grid(collection_frame(records), columns=min(5, len(records)), spacing=96)[["filename", "x", "y"]]
            workspace["coordinates"] = grid.to_dict(orient="records"); workspace["coordinate_source"] = "generated_qa_grid"
            workspace["regional"] = None
            st.success("Collection analyzed. Overview, gallery, spatial visualization, and records are ready.")

else:
    upload = st.file_uploader(
        "Upload a larger PNG, JPEG, or TIFF image",
        type=["png", "jpg", "jpeg", "tif", "tiff"],
        key="large",
        max_upload_size=25,
        help=(
            "Maximum compressed upload size: 25 MB. "
            "Decoded images are also limited by pixel count and tile count."
        ),
    )

    a, b, c = st.columns(3)
    stride = a.selectbox(
        "Tile stride",
        [96, 48],
        index=0,
        help=(
            "96 gives non-overlapping tiles. "
            "48 gives a denser overlapping visualization."
        ),
    )
    exclude_blank = b.checkbox(
        "Exclude blank-like tiles",
        value=True,
    )
    mpp_text = c.text_input(
        "Microns per pixel, optional",
        value="",
    )

    if upload is None:
        st.info(
            "Select a large image. The app will immediately show a "
            "preflight summary and then enable analysis when the image "
            "fits the configured limits."
        )
    else:
        data = upload.getvalue()

        try:
            large_image_preflight = inspect_large_image(data)
            st.caption(
                f"Preflight: {large_image_preflight['width']:,} x "
                f"{large_image_preflight['height']:,} pixels, "
                f"{large_image_preflight['megapixels']:.1f} MP, estimated base RGB "
                f"{large_image_preflight['estimated_rgb_bytes'] / 1048576:.1f} MB."
            )
            preview_image = decode_large_image(data)
            tiles_across = (
                ((preview_image.width - 96) // stride) + 1
                if preview_image.width >= 96
                else 0
            )
            tiles_down = (
                ((preview_image.height - 96) // stride) + 1
                if preview_image.height >= 96
                else 0
            )
            expected_tiles = tiles_across * tiles_down
            decoded_pixels = preview_image.width * preview_image.height

            p1, p2, p3, p4 = st.columns(4)
            p1.metric(
                "Image dimensions",
                f"{preview_image.width:,} x {preview_image.height:,}",
            )
            p2.metric(
                "Decoded pixels",
                f"{decoded_pixels:,}",
            )
            p3.metric(
                "Expected tiles",
                f"{expected_tiles:,}",
            )
            p4.metric(
                "Tile limit",
                "1,000",
            )

            image_is_large_enough = (
                preview_image.width >= 96
                and preview_image.height >= 96
            )
            tile_count_is_safe = 1 <= expected_tiles <= 1_000
            ready_for_analysis = (
                image_is_large_enough
                and tile_count_is_safe
            )

            if not image_is_large_enough:
                st.error(
                    "The image is smaller than 96 x 96. "
                    "Use Single patch instead."
                )
            elif not tile_count_is_safe:
                st.error(
                    "This setting would create "
                    f"{expected_tiles:,} tiles, exceeding the 1,000-tile "
                    "safety limit. Use a smaller crop or stride 96."
                )
            else:
                st.success(
                    "Preflight passed. Click Analyze large image to start "
                    "tile extraction and inference."
                )

            analyze_large_image = st.button(
                "Analyze large image",
                type="primary",
                disabled=not ready_for_analysis,
                use_container_width=True,
            )

            if analyze_large_image:
                mpp = float(mpp_text) if mpp_text.strip() else None
                config = TileConfig(stride=stride)
                tiles = extract_tiles(preview_image, config)
                records = []
                bar = st.progress(0)

                for index, tile in enumerate(tiles, start=1):
                    included = (
                        not tile["blank_like"]
                        if exclude_blank
                        else True
                    )
                    result = (
                        predict_image(
                            decode_uploaded_image(tile["bytes"]),
                            model(),
                        ).to_dict()
                        if included
                        else {}
                    )
                    records.append(
                        {
                            k: v
                            for k, v in tile.items()
                            if k != "bytes"
                        }
                        | {
                            "score": result.get("score"),
                            "threshold_prediction": result.get(
                                "threshold_prediction"
                            ),
                            "threshold_interpretation": result.get(
                                "threshold_interpretation"
                            ),
                            "included_in_inference": included,
                            "stride": stride,
                        }
                    )
                    bar.progress(index / len(tiles))

                frame = pd.DataFrame(records)
                workspace["regional"] = {
                    "filename": upload.name,
                    "image_bytes": data,
                    "image_sha256": hashlib.sha256(data).hexdigest(),
                    "width": preview_image.width,
                    "height": preview_image.height,
                    "mpp": mpp,
                    "stride": stride,
                    "tiles": records,
                    "summary": spatial_coverage_summary(
                        frame,
                        preview_image.width,
                        preview_image.height,
                        mpp,
                    ),
                }
                workspace["collection"] = [
                    {
                        "filename": row["filename"],
                        "score": row["score"],
                        "threshold_prediction": row[
                            "threshold_prediction"
                        ],
                        "threshold_interpretation": row[
                            "threshold_interpretation"
                        ],
                        "width": 96,
                        "height": 96,
                        "original_mode": "RGB",
                        "image_sha256": row["image_sha256"],
                        "error": (
                            None
                            if row["included_in_inference"]
                            else "excluded_blank_like"
                        ),
                    }
                    for row in records
                ]
                workspace["coordinates"] = [
                    {
                        "filename": row["filename"],
                        "x": row["x"],
                        "y": row["y"],
                    }
                    for row in records
                ]
                workspace["coordinate_source"] = (
                    "large_image_authentic_pixel_coordinates"
                )
                st.success(
                    "Large-image tiled analysis is complete. Open Results "
                    "Overview, Spatial Analysis, or Patch Gallery."
                )

        except ValueError as error:
            st.error(str(error))
st.info("The frozen classifier produces one score per 96 x 96 tile. Tiled coverage is not a pixel-level tumor segmentation or malignant-area measurement.")
footer()
