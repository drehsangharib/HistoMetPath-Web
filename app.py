import streamlit as st
from histometpath_web.ui import configure, footer
configure("Home")
st.markdown("""<div class="hero"><div class="kicker">Open-source computational pathology</div><h1>HistoMetPath Web</h1><p>From patches to slide-level evidence—with reproducibility and evaluation integrity built in.</p></div>""", unsafe_allow_html=True)
left,right=st.columns([1.5,1])
with left:
 st.subheader("Explore the framework")
 st.write("HistoMetPath Web is a synthetic-only interactive companion to the HistoMetPath research framework. Explore leakage-safe pseudo-slides, spatial sampling, MIL aggregation, and evaluation governance without accessing restricted cohorts or executing the sealed external pilot.")
 st.markdown("""**Pipeline**

`Patch-level data` → `Leakage-safe pseudo-slides` → `Spatial sampling` → `Tile representations` → `MIL aggregation` → `Calibration & uncertainty` → `Frozen evaluation governance`""")
 c1,c2=st.columns(2);c1.link_button("Open GitHub repository","https://github.com/drehsangharib/HistoMetPath",width='stretch');c2.link_button("Open development release","https://github.com/drehsangharib/HistoMetPath/releases/tag/development-release-2251265",width='stretch')
with right:
 st.markdown('<div class="status"><b>Development framework</b><br>Published and CI-green</div>',unsafe_allow_html=True)
 st.markdown('<div class="status"><b>CAMELYON16</b><br>Held-out evaluation complete and immutable</div>',unsafe_allow_html=True)
 st.markdown('<div class="warn"><b>CAMELYON17</b><br>Sealed and unexecuted • 0 of 1</div>',unsafe_allow_html=True)
st.subheader("What changed since the initial release?")
a,b=st.columns(2)
with a:
 st.markdown("**Initial foundation**")
 st.markdown("- Patch classification\n- Embedding extraction\n- Pseudo-slide MIL\n- Attention visualization")
with b:
 st.markdown("**Current framework**")
 st.markdown("- Leakage-safe split controls\n- Spatial sampling and WSI workflows\n- Calibration, uncertainty, and stability analysis\n- Frozen evaluation contracts and audited releases")
footer()
