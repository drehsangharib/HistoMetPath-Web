import streamlit as st

from histometpath_web.workspace import collection_frame, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Framework")
st.title("Framework and Current Workspace")
st.write("HistoMetPath separates patch inference, collection summaries, spatial visualization, and evaluation governance into explicit stages.")
workspace = ensure_workspace(st.session_state)
frame = collection_frame(workspace["collection"])
single = workspace["single_patch"]
coordinates = workspace["coordinates"]

st.subheader("Current browser-session workspace")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Single patch", "Ready" if single else "None")
c2.metric("Collection patches", len(frame))
c3.metric("Coordinates", len(coordinates) if coordinates else 0)
c4.metric("Spatial map", "Ready" if coordinates and not frame.empty else "Unavailable")

if frame.empty:
    st.info("Analyze 2 to 100 patches under Patch Collection Analysis to activate collection summaries and an automatic QA spatial grid.")
else:
    st.success("The patch collection is analyzed and shared across all data-driven pages. No repeated image upload is required.")
    st.caption(f'Coordinate source: {workspace.get("coordinate_source") or "not connected"}')

st.subheader("Capability map")
capabilities = [
    ("Single-patch inference", "Available" if single else "Upload one patch", "Real frozen patch-model inference"),
    ("Patch collection analysis", "Available" if not frame.empty else "Upload multiple patches", "Real per-patch inference and descriptive summaries"),
    ("Spatial patch map", "Available" if coordinates and not frame.empty else "Requires analyzed collection", "Automatic QA grid or original user coordinates"),
    ("Patch-set summaries", "Available" if not frame.empty else "Requires analyzed collection", "Descriptive mean, maximum, median, top-k mean, and fraction above threshold"),
    ("Validated slide-level MIL", "Not available", "Requires a separately audited and frozen bag-level model"),
    ("Clinical diagnosis", "Not supported", "Research demonstration only"),
]
for title, status, detail in capabilities:
    with st.container(border=True):
        st.markdown(f"### {title}")
        st.markdown(f"**Status:** {status}")
        st.write(detail)
footer()
