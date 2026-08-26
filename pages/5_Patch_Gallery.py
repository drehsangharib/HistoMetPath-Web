import io
import pandas as pd
import streamlit as st
from PIL import Image

from histometpath_web.workspace import collection_frame, ensure_workspace
from histometpath_web.ui import configure, footer

configure("Patch Gallery")
st.title("Patch Gallery")
workspace = ensure_workspace(st.session_state); frame = collection_frame(workspace["collection"])
if frame.empty:
    st.info("Run an analysis first.")
else:
    valid = frame[frame["error"].isna()].copy()
    view = st.selectbox("Gallery view", ["Highest scores", "Lowest scores", "Closest to threshold"])
    if view == "Highest scores": selected = valid.nlargest(12, "score")
    elif view == "Lowest scores": selected = valid.nsmallest(12, "score")
    else: selected = valid.assign(distance=(valid["score"] - 0.5).abs()).nsmallest(12, "distance")
    regional = workspace.get("regional")
    tile_bytes = {}
    if regional:
        from histometpath_web.regional_analysis import TileConfig, decode_large_image, extract_tiles
        for tile in extract_tiles(decode_large_image(regional["image_bytes"]), TileConfig(stride=regional["stride"])):
            tile_bytes[tile["filename"]] = tile["bytes"]
    columns = st.columns(4)
    for index, row in enumerate(selected.itertuples()):
        with columns[index % 4]:
            if row.filename in tile_bytes:
                st.image(Image.open(io.BytesIO(tile_bytes[row.filename])), width="stretch")
            st.markdown(f"**{row.filename}**")
            st.write(f"Score: {row.score:.4f}")
            st.caption(row.threshold_interpretation)
    st.info("Gallery ranking helps inspect model outputs and input quality. It does not identify confirmed malignant tissue.")
footer()
