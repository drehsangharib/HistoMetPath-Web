import json
import platform
import subprocess
import streamlit as st
import torch, torchvision

from histometpath_web.inference import EXPECTED_MODEL_SHA256
from histometpath_web.workspace import collection_frame, collection_summary, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Analysis Record")
st.title("Analysis Record")
workspace = ensure_workspace(st.session_state); frame = collection_frame(workspace["collection"]); summary = collection_summary(frame)
try: commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception: commit = "unknown"
record = {
    "application_commit": commit, "python": platform.python_version(), "pytorch": torch.__version__,
    "torchvision": torchvision.__version__, "streamlit": st.__version__, "model_sha256": EXPECTED_MODEL_SHA256,
    "historical_threshold": 0.5, "threshold_modified": False, "collection_summary": summary,
    "coordinate_source": workspace.get("coordinate_source"), "large_image_analysis": workspace.get("regional") is not None,
    "protected_evaluation_accessed": False, "external_execution_consumed": False, "clinical_use": False,
}
st.subheader("Technical provenance"); st.json(record)
st.subheader("Interpretation boundaries")
st.write("The application analyzes user-provided images only. It does not access protected evaluation cohorts.")
st.write("Patch scores and tiled coverage are research-model outputs, not diagnosis, tumor burden, or malignant-area segmentation.")
st.write("Generated QA coordinates are not tissue anatomy. Large-image tile coordinates do preserve uploaded-image geometry.")
st.download_button("Download analysis record JSON", json.dumps(record, indent=2), "histometpath_analysis_record.json", "application/json")
footer()
