import streamlit as st
from histometpath_web.ui import configure, footer

configure("About and Limitations")
st.title("About and Limitations")
st.write("HistoMetPath-Web is a research demonstration for patch-level and tiled regional analysis of breast histopathology images.")
st.subheader("Supported")
for item in ["Single 96 x 96 patch inference", "Multiple-patch inference", "Large-image tiling into 96 x 96 regions", "Authentic uploaded-image tile coordinates", "Descriptive score distributions, galleries, coverage, and non-overlapping spatial clusters", "Downloadable analysis records"]:
    st.write("- " + item)
st.subheader("Not supported")
for item in ["Direct browser upload or execution of whole-slide images", "Clinical diagnosis", "Patient-level cancer probability", "Validated slide-level MIL prediction", "Pixel-level tumor segmentation", "Malignant-area measurement", "Tumor boundary delineation", "Automatic inference of physical scale when microns-per-pixel is unknown"]:
    st.write("- " + item)
st.info("A validated tumor-segmentation model and pixel-level annotations would be required before reporting estimated malignant area.")
footer()
