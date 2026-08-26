import pandas as pd
import plotly.express as px
import streamlit as st

from histometpath_web.workspace import collection_frame, collection_summary, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Patch-Set Summaries")
st.title("Patch-Set Summaries")
st.caption("Real descriptive pooling of the current patch collection")
st.warning("These are descriptive patch-set summaries, not outputs from a validated slide-level MIL model. Mean or maximum patch score must not be interpreted as patient-level cancer probability.")
workspace = ensure_workspace(st.session_state)
frame = collection_frame(workspace["collection"])
valid = frame[frame["error"].isna()].copy() if not frame.empty else frame
if valid.empty:
    st.info("First analyze multiple patches under Patch Collection Analysis.")
else:
    scores = pd.to_numeric(valid["score"])
    top_k = st.slider("Top-k patches for top-k mean", 1, min(20, len(scores)), min(5, len(scores)))
    summaries = {
        "Mean patch score": float(scores.mean()),
        "Maximum patch score": float(scores.max()),
        f"Top-{top_k} mean": float(scores.nlargest(top_k).mean()),
        "Median patch score": float(scores.median()),
        "Fraction above 0.50": float((scores >= 0.5).mean()),
    }
    columns = st.columns(len(summaries))
    for column, (label, value) in zip(columns, summaries.items()):
        column.metric(label, f"{value:.4f}")
    ranked = valid.sort_values("score", ascending=False).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    st.plotly_chart(px.bar(ranked.head(30), x="filename", y="score", color="threshold_prediction", title="Highest-scoring patches, maximum 30 shown"), width="stretch")
    st.dataframe(ranked[["rank", "filename", "score", "threshold_interpretation"]], width="stretch", hide_index=True)
    st.info("A true MIL page will require a separately audited and frozen bag-level model artifact. This page intentionally does not manufacture a slide prediction from patch scores.")
footer()
