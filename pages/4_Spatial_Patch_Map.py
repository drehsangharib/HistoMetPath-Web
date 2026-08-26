import pandas as pd
import plotly.express as px
import streamlit as st

from histometpath_web.workspace import collection_frame, ensure_workspace, generated_qa_grid, validate_coordinate_frame
from histometpath_web.ui import configure, footer

configure("Spatial Patch Map")
st.title("Spatial Patch Map")
st.caption("Coordinate-aware visualization of real patch scores")
st.warning("Original coordinates are preferred. A generated QA grid tests the interface but is not tissue anatomy.")
workspace = ensure_workspace(st.session_state)
frame = collection_frame(workspace["collection"])
if frame.empty:
    st.info("First analyze multiple patches under Patch Collection Analysis.")
else:
    st.write(f"Current collection: {len(frame)} files")
    method = st.radio("Coordinate source", ["Upload original coordinate CSV", "Generate QA grid"], horizontal=True)
    if method == "Upload original coordinate CSV":
        upload = st.file_uploader("Upload CSV with exact columns filename,x,y", type=["csv"])
        if upload is not None:
            try:
                validated = validate_coordinate_frame(pd.read_csv(upload), set(frame["filename"]))
                workspace["coordinates"] = validated.to_dict(orient="records")
                workspace["coordinate_source"] = "user_provided"
                st.success("Coordinates validated and connected to the current collection.")
            except Exception as error:
                st.error(str(error))
    else:
        a, b = st.columns(2)
        columns = a.number_input("Grid columns", 1, 20, min(5, len(frame)))
        spacing = b.number_input("Grid spacing", 1, 4096, 96)
        if st.button("Generate and connect QA grid", type="primary"):
            grid = generated_qa_grid(frame, columns, spacing)[["filename", "x", "y"]]
            workspace["coordinates"] = grid.to_dict(orient="records")
            workspace["coordinate_source"] = "generated_qa_grid"
            st.success("Generated QA grid connected. This is not original tissue geometry.")
    if workspace["coordinates"]:
        coordinates = pd.DataFrame(workspace["coordinates"])
        mapped = coordinates.merge(frame, on="filename", how="left", validate="one_to_one")
        mapped["category"] = mapped["threshold_prediction"].map({1: "Above 0.50", 0: "Below 0.50"}).fillna("Unavailable")
        st.info(f'Coordinate source: {workspace["coordinate_source"]}')
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Collection patches", len(frame)); m2.metric("Coordinate rows", len(coordinates))
        m3.metric("Matched", mapped["score"].notna().sum()); m4.metric("Unmatched", mapped["score"].isna().sum())
        color_by = st.selectbox("Color map by", ["score", "category"])
        fig = px.scatter(mapped, x="x", y="y", color=color_by, hover_name="filename",
                         hover_data=["score", "category"], range_color=[0, 1] if color_by == "score" else None,
                         title="Spatial patch map")
        fig.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1)
        st.plotly_chart(fig, width="stretch")
        st.dataframe(mapped.sort_values(["y", "x"]), width="stretch", hide_index=True)
        st.download_button("Download merged spatial results CSV", mapped.to_csv(index=False), "histometpath_spatial_patch_map.csv", "text/csv")
    else:
        st.info("No coordinates are connected yet.")
footer()
