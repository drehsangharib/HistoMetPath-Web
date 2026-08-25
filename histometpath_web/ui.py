import streamlit as st

def configure(title: str):
    st.set_page_config(page_title=f"{title} | HistoMetPath Web", page_icon="🔬", layout="wide")
    st.markdown("""<style>
    .block-container{padding-top:2rem;max-width:1200px}.hero{padding:2rem;border-radius:18px;background:linear-gradient(135deg,#0b2239,#146c7e);color:white;margin-bottom:1.2rem}.kicker{letter-spacing:.12em;text-transform:uppercase;font-size:.78rem;opacity:.82}.muted{color:#586174}.status{padding:.7rem 1rem;border-left:4px solid #1c8c78;background:#f1fbf8;border-radius:6px}.warn{padding:.7rem 1rem;border-left:4px solid #d39b20;background:#fff8e7;border-radius:6px}
    </style>""", unsafe_allow_html=True)

def footer():
    st.divider();st.caption("Research demonstration only • Not a medical device • No CAMELYON17 inference • No patient-care use")
