import json
import platform
import subprocess

import streamlit as st
import torch
import torchvision

from histometpath_web import __version__
from histometpath_web.inference import EXPECTED_MODEL_SHA256
from histometpath_web.workspace import collection_frame, collection_summary, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Reproducibility")
st.title("Reproducibility Dashboard")
st.write("Live environment, model provenance, and current-session analysis metadata.")
workspace = ensure_workspace(st.session_state)
frame = collection_frame(workspace["collection"])
summary = collection_summary(frame)
try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception:
    commit = "unknown"

r1, r2, r3, r4 = st.columns(4)
r1.metric("App version", __version__)
r2.metric("Collection patches", summary["analyzed"])
r3.metric("Inference device", "CPU")
r4.metric("Coordinate source", workspace.get("coordinate_source") or "none")

st.subheader("Software environment")
environment = {
    "application_commit": commit,
    "application_version": __version__,
    "python": platform.python_version(),
    "pytorch": torch.__version__,
    "torchvision": torchvision.__version__,
    "streamlit": st.__version__,
    "inference_device": "cpu",
}
st.json(environment)

st.subheader("Model integrity contract")
st.code(
    "Release: model-v1\n"
    "Expected size: 45,839,941 bytes\n"
    "Expected SHA-256: " + EXPECTED_MODEL_SHA256 + "\n"
    "Historical threshold: 0.50\n"
    "Loading mode: weights_only=True"
)

st.subheader("Current-session analysis")
analysis = {
    "single_patch_available": workspace["single_patch"] is not None,
    "collection_summary": summary,
    "coordinate_rows": len(workspace["coordinates"] or []),
    "coordinate_source": workspace.get("coordinate_source"),
    "threshold_modified": False,
    "clinical_use": False,
    "external_execution_consumed": False,
}
st.json(analysis)
receipt = {"environment": environment, "model_sha256": EXPECTED_MODEL_SHA256, "analysis": analysis}
st.download_button("Download reproducibility receipt JSON", json.dumps(receipt, indent=2), "histometpath_reproducibility_receipt.json", "application/json")
st.info("Framework and governance pages are intentionally informational, but both now reflect the current browser-session workspace and provide downloadable receipts.")
footer()
