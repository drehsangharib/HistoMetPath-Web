import streamlit as st
from histometpath_web.ui import configure,footer
configure("Reproducibility")
st.title("Reproducibility and release")
st.markdown("""The research repository provides configuration-driven workflows, automated tests, CI, decision records, and checksum-backed release assets.

**Published development release**
`development-release-2251265`

**Released commit**
`22512657feb230e50613be7d5b2a9f0624c9461e`

**Source ZIP SHA-256**
`4d37cb00ffa8408d42072668621ed0ca45ad9a6fc361cb82f1b17c5875115af4`
""")
st.link_button("View audited release","https://github.com/drehsangharib/HistoMetPath/releases/tag/development-release-2251265")
st.code("py -3.11 -m pip install -r requirements.txt\npy -3.11 -m pytest tests -v",language="powershell")
st.info("HistoMetPath Web is a separate synthetic-only companion. The scientific repository remains the source of truth.")
footer()
