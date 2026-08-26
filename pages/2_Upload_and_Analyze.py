from pathlib import Path
import json

import streamlit as st

from histometpath_web.model_acquisition import ModelAcquisitionError, acquire_model
from histometpath_web.inference import EXPECTED_MODEL_SHA256, ImageValidationError, decode_uploaded_image, load_inference_model, predict_image
from histometpath_web.workspace import clear_workspace, ensure_workspace, image_sha256
from histometpath_web.ui import configure, footer

configure("Single-Patch Analysis")
st.title("Single-Patch Analysis")
st.caption("Real patch-level breast histopathology research inference")
st.warning("Research demonstration only. This page analyzes one uploaded patch. It is not a diagnosis, patient-level result, or calibrated cancer probability.")
workspace = ensure_workspace(st.session_state)

with st.sidebar:
    st.markdown("### Current analysis")
    if workspace["single_patch"]:
        item = workspace["single_patch"]
        st.write(item["filename"])
        st.metric("Score", f'{item["result"]["score"]:.4f}')
        st.caption(item["result"]["threshold_interpretation"])
    else:
        st.caption("No persistent patch result yet.")
    if st.button("Clear analysis workspace", use_container_width=True):
        clear_workspace(st.session_state)
        st.rerun()

with st.expander("Validated model contract"):
    st.code("Architecture: ResNet-18\nInput: RGB resized to 96 x 96\nOutput: sigmoid research score\nHistorical threshold: 0.5\nArtifact SHA-256: " + EXPECTED_MODEL_SHA256)

uploaded = st.file_uploader("Upload one PNG or JPEG histopathology patch", type=["png", "jpg", "jpeg"])
if uploaded is not None:
    try:
        data = uploaded.getvalue()
        image = decode_uploaded_image(data)
        local = Path(__file__).resolve().parents[1] / "local_model_artifacts" / "histometpath_resnet18_patch_state_dict.pt"
        with st.spinner("Acquiring and verifying the frozen model..."):
            model_path = acquire_model(local_override=local if local.is_file() else None)
            model, _ = load_inference_model(model_path)
            result = predict_image(image, model)
        workspace["single_patch"] = {"filename": uploaded.name, "bytes": data, "image_sha256": image_sha256(data), "result": result.to_dict()}
    except (ImageValidationError, ModelAcquisitionError, Exception) as error:
        st.error(f"Analysis could not be completed: {error}")

item = workspace.get("single_patch")
if item:
    image = decode_uploaded_image(item["bytes"])
    result = item["result"]
    st.image(image, caption=f'Current patch: {item["filename"]} | {result["width"]} x {result["height"]}, mode {result["original_mode"]}', width="stretch")
    left, right = st.columns(2)
    left.metric("Tumor-associated research score", f'{result["score"]:.4f}')
    right.metric("Historical threshold", f'{result["historical_threshold"]:.2f}')
    (st.warning if result["threshold_prediction"] == 1 else st.success)(result["threshold_interpretation"])
    st.caption("This result persists while navigating this browser session. Other data-driven pages use the patch collection, not this one patch.")
    report = {"analysis_type": "single patch", "filename": item["filename"], "image_sha256": item["image_sha256"], "result": result}
    st.download_button("Download research result JSON", json.dumps(report, indent=2), "histometpath_patch_result.json", "application/json")
else:
    st.info("Upload a patch to create a persistent session result.")
footer()
