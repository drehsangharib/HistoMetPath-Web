import json
import subprocess

import streamlit as st

from histometpath_web.inference import EXPECTED_MODEL_SHA256
from histometpath_web.workspace import collection_frame, collection_summary, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Evaluation Governance")
st.title("Evaluation Governance")
st.write("HistoMetPath treats evaluation data as a governed resource, not a repeatedly queried benchmark.")
workspace = ensure_workspace(st.session_state)
frame = collection_frame(workspace["collection"])
summary = collection_summary(frame)

st.subheader("Current-session governance receipt")
g1, g2, g3, g4 = st.columns(4)
g1.metric("Collection patches", summary["analyzed"])
g2.metric("Historical threshold", "0.50")
g3.metric("Threshold modified", "No")
g4.metric("External execution", "0 of 1")
st.code(
    "Model SHA-256: " + EXPECTED_MODEL_SHA256 + "\n"
    "Analysis level: patch / patch collection\n"
    "Coordinate source: " + str(workspace.get("coordinate_source") or "none") + "\n"
    "PCAM test accessed: No\nCAMELYON16 final test rerun: No\nCAMELYON17 accessed: No\nExternal execution consumed: No"
)

items = [
    ("CAMELYON16 held-out evaluation", "Complete and immutable", "The recorded small development benchmark must not be rerun or tuned against."),
    ("CAMELYON17 external pilot", "Sealed and unexecuted", "The pilot remains preserved for one deliberate future evaluation."),
    ("External execution", "Disabled", "The web app has no token, lock access, or external inference pathway."),
]
for title, status, detail in items:
    with st.container(border=True):
        st.markdown(f"### {title}"); st.markdown(f"**Status:** {status}"); st.write(detail)

st.subheader("Practice decision")
choice = st.radio("Which action preserves evaluation integrity?", [
    "Tune the threshold after seeing external outcomes",
    "Repeat external runs until metrics stabilize",
    "Freeze development choices before one external run",
], index=None)
if choice is not None:
    if choice.startswith("Freeze"):
        st.success("Correct: freeze development choices first.")
    else:
        st.error("That action would compromise the evaluation boundary.")

try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception:
    commit = "unknown"
receipt = {
    "application_commit": commit,
    "model_sha256": EXPECTED_MODEL_SHA256,
    "historical_threshold": 0.5,
    "threshold_modified": False,
    "analysis_level": "patch_collection" if not frame.empty else "none",
    "patch_count": summary["analyzed"],
    "coordinate_source": workspace.get("coordinate_source"),
    "pcam_test_accessed": False,
    "camelyon16_final_test_rerun": False,
    "camelyon17_accessed": False,
    "external_execution_consumed": False,
    "clinical_use": False,
}
st.download_button("Download governance receipt JSON", json.dumps(receipt, indent=2), "histometpath_governance_receipt.json", "application/json")
footer()
