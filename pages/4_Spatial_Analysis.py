import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
import io

from histometpath_web.regional_analysis import connected_components, overlay_png
from histometpath_web.workspace import collection_frame, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Spatial Analysis")
st.title("Spatial Analysis")
workspace = ensure_workspace(st.session_state); frame = collection_frame(workspace["collection"])
if frame.empty or not workspace["coordinates"]:
    st.info("Run a patch-collection or large-image analysis first.")
else:
    mapped = pd.DataFrame(workspace["coordinates"]).merge(frame, on="filename", how="left", validate="one_to_one")
    mapped["included_in_inference"] = mapped["error"].isna()
    mapped["stride"] = workspace.get("regional", {}).get("stride", 96) if workspace.get("regional") else 96
    mapped["category"] = mapped["threshold_prediction"].map({1: "Above 0.50", 0: "Below 0.50"}).fillna("Excluded")
    source = workspace.get("coordinate_source")
    st.info(f"Coordinate source: {source}")
    if source == "generated_qa_grid":
        st.warning("The generated QA grid is not original tissue geometry. Area and clustering interpretations are disabled.")
    else:
        clusters = connected_components(mapped) if mapped["stride"].eq(96).all() else pd.DataFrame()
        if not clusters.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Above-threshold clusters", len(clusters)); c2.metric("Largest cluster, tiles", int(clusters.iloc[0]["tile_count"]))
            c3.metric("Largest-cluster max score", f'{clusters.iloc[0]["max_score"]:.4f}')
            st.dataframe(clusters, width="stretch", hide_index=True)
    fig = px.scatter(mapped, x="x", y="y", color="score", hover_name="filename", hover_data=["category"], range_color=[0, 1], title="Patch or tile score map")
    fig.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, width="stretch")
    regional = workspace.get("regional")
    if regional:
        image = Image.open(io.BytesIO(regional["image_bytes"])).convert("RGB")
        st.image(overlay_png(image, mapped), caption="Classifier-score overlay. This is not a tumor segmentation mask.", width="stretch")
    st.download_button("Download spatial analysis CSV", mapped.to_csv(index=False), "histometpath_spatial_analysis.csv", "text/csv")
footer()
