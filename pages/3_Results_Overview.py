import pandas as pd
import plotly.express as px
import streamlit as st

from histometpath_web.workspace import collection_frame, collection_summary, ensure_workspace, duplicate_groups
from histometpath_web.ui import configure, footer

configure("Results Overview")
st.title("Results Overview")
workspace = ensure_workspace(st.session_state); frame = collection_frame(workspace["collection"])
if frame.empty:
    st.info("Run an analysis first.")
else:
    summary = collection_summary(frame)
    a, b, c, d = st.columns(4)
    a.metric("Analyzed patches or tiles", summary["analyzed"]); b.metric("Above 0.50", summary["above"])
    c.metric("Below 0.50", summary["below"]); d.metric("Rejected or excluded", summary["rejected"])
    valid = frame[frame["error"].isna()].copy()
    if not valid.empty:
        e, f, g, h = st.columns(4)
        e.metric("Mean score", f'{summary["mean"]:.4f}'); f.metric("Median", f'{summary["median"]:.4f}')
        g.metric("Minimum", f'{summary["minimum"]:.4f}'); h.metric("Maximum", f'{summary["maximum"]:.4f}')
        st.plotly_chart(px.histogram(valid, x="score", nbins=25, range_x=[0, 1], title="Score distribution"), width="stretch")
        valid["distance_from_threshold"] = (valid["score"] - 0.5).abs()
        st.subheader("Near-threshold observations")
        st.dataframe(valid.nsmallest(10, "distance_from_threshold")[["filename", "score", "threshold_interpretation", "distance_from_threshold"]], width="stretch", hide_index=True)
    duplicates = duplicate_groups(frame)
    if duplicates:
        st.warning("Duplicate image content: " + "; ".join(", ".join(group) for group in duplicates))
    regional = workspace.get("regional")
    if regional:
        st.subheader("Large-image coverage summary")
        st.json(regional["summary"])
        st.warning("Above-threshold tile fraction and represented area are classifier coverage summaries, not malignant area or tumor burden.")
footer()
