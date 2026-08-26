from pathlib import Path
import json
import subprocess

import pandas as pd
import plotly.express as px
import streamlit as st

from histometpath_web.inference import decode_uploaded_image, load_inference_model, predict_image, EXPECTED_MODEL_SHA256
from histometpath_web.model_acquisition import acquire_model
from histometpath_web.workspace import (build_session_bundle, collection_frame, collection_summary,
    coordinate_template, duplicate_groups, ensure_workspace, generated_qa_grid, image_sha256)
from histometpath_web.ui import configure, footer

configure("Patch Collection Analysis")
st.title("Patch Collection Analysis")
st.caption("Real per-patch inference and a self-contained handoff to spatial mapping")
st.warning("Collection summaries depend on user-selected patches. They are not a validated slide diagnosis or tumor-burden estimate.")
workspace = ensure_workspace(st.session_state)
files = st.file_uploader("Upload 2 to 100 PNG/JPEG patches", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if st.button("Analyze patch collection", type="primary", disabled=not files):
    if not 2 <= len(files) <= 100:
        st.error("Upload between 2 and 100 patches.")
    else:
        local = Path(__file__).resolve().parents[1] / "local_model_artifacts" / "histometpath_resnet18_patch_state_dict.pt"
        model_path = acquire_model(local_override=local if local.is_file() else None)
        model, _ = load_inference_model(model_path)
        records, progress = [], st.progress(0)
        for position, upload in enumerate(files, start=1):
            data = upload.getvalue(); base = {"filename": upload.name, "image_sha256": image_sha256(data), "error": None}
            try:
                result = predict_image(decode_uploaded_image(data), model).to_dict()
                records.append({**base, **result})
            except Exception as error:
                records.append({**base, "score": None, "threshold_prediction": None, "threshold_interpretation": None,
                                "width": None, "height": None, "original_mode": None, "error": str(error)})
            progress.progress(position / len(files))
        workspace["collection"] = records
        default_grid = generated_qa_grid(collection_frame(records), columns=min(5, len(records)), spacing=96)[["filename", "x", "y"]]
        workspace["coordinates"] = default_grid.to_dict(orient="records")
        workspace["coordinate_source"] = "generated_qa_grid"
        st.success(f"Analyzed {len(files)} uploaded files.")

frame = collection_frame(workspace["collection"])
if frame.empty:
    st.info("Upload a patch collection. Results persist across pages for this browser session.")
else:
    summary = collection_summary(frame)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Uploaded", summary["uploaded"]); c2.metric("Analyzed", summary["analyzed"])
    c3.metric("Above 0.50", summary["above"]); c4.metric("Rejected", summary["rejected"])
    if summary["analyzed"]:
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Fraction above", f'{summary["fraction_above"]:.1%}'); d2.metric("Median", f'{summary["median"]:.4f}')
        d3.metric("Minimum", f'{summary["minimum"]:.4f}'); d4.metric("Maximum", f'{summary["maximum"]:.4f}')
        valid = frame[frame["error"].isna()].copy()
        st.plotly_chart(px.histogram(valid, x="score", nbins=20, range_x=[0, 1], title="Patch-score distribution"), width="stretch")
        tabs = st.tabs(["Highest scores", "Lowest scores", "Closest to threshold"])
        tabs[0].dataframe(valid.sort_values("score", ascending=False).head(10), width="stretch", hide_index=True)
        tabs[1].dataframe(valid.sort_values("score").head(10), width="stretch", hide_index=True)
        near = valid.assign(distance=(valid["score"] - 0.5).abs()).sort_values("distance").head(10)
        tabs[2].dataframe(near, width="stretch", hide_index=True)
    duplicates = duplicate_groups(frame)
    if duplicates:
        st.warning("Duplicate image content detected: " + "; ".join(", ".join(group) for group in duplicates))
    st.subheader("Downloads and spatial handoff")
    st.download_button("1. Download inference results CSV", frame.to_csv(index=False), "histometpath_patch_inference_results.csv", "text/csv")
    st.download_button("2. Download blank coordinate template", coordinate_template(frame).to_csv(index=False), "histometpath_coordinate_template.csv", "text/csv")
    g1, g2 = st.columns(2)
    grid_columns = g1.number_input("QA-grid columns", 1, 20, min(5, len(frame)))
    grid_spacing = g2.number_input("QA-grid spacing", 1, 4096, 96)
    qa_grid = generated_qa_grid(frame, grid_columns, grid_spacing)
    st.download_button("3. Download generated QA grid", qa_grid.to_csv(index=False), "histometpath_generated_qa_grid.csv", "text/csv")
    st.caption("Generated QA coordinates are for interface testing only and do not represent original tissue geometry.")
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    coords = pd.DataFrame(workspace["coordinates"]) if workspace["coordinates"] else None
    bundle = build_session_bundle(frame, coords, workspace["coordinate_source"], EXPECTED_MODEL_SHA256, commit)
    st.download_button("Download complete analysis bundle ZIP", bundle, "histometpath_analysis_bundle.zip", "application/zip")
footer()
