import streamlit as st
from histometpath_web.ui import configure,footer
configure("Framework")
st.title("Framework overview")
st.write("HistoMetPath separates model development, calibration, held-out evaluation, and external execution into explicit stages.")
steps=[("1","Split integrity","Define training, validation, and held-out units before bags are constructed."),("2","Pseudo-slide construction","Build deterministic bags without crossing split boundaries."),("3","Spatial sampling","Balance tissue coverage and spatial diversity."),("4","Tile representations","Create fixed tile-level features for slide aggregation."),("5","MIL aggregation","Compare mean, max, and attention-based summaries."),("6","Evaluation governance","Freeze development choices before held-out or external evaluation.")]
for num,title,text in steps:
 with st.container(border=True): st.markdown(f"### {num}. {title}");st.write(text)
st.info("This demo illustrates framework logic using generated examples. It does not reproduce or execute the sealed external pilot.")
footer()
