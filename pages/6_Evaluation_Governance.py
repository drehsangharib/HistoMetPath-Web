import streamlit as st

from histometpath_web.ui import configure, footer


configure("Evaluation governance")

st.title("Evaluation governance")

st.write(
    "HistoMetPath treats evaluation data as a governed resource, "
    "not a repeatedly queried benchmark."
)

governance_items = [
    (
        "CAMELYON16 held-out evaluation",
        "Complete and immutable",
        "The recorded small development benchmark must not be rerun "
        "or tuned against.",
    ),
    (
        "CAMELYON17 external pilot",
        "Sealed and unexecuted",
        "The pilot remains preserved for one deliberate future evaluation.",
    ),
    (
        "External execution",
        "Disabled",
        "The web app has no token, lock access, or external inference pathway.",
    ),
    (
        "Execution count",
        "0 of 1",
        "Nothing in this app can change the external execution count.",
    ),
]

for title, status, detail in governance_items:
    with st.container(border=True):
        st.markdown(f"### {title}")
        st.markdown(f"**Status:** {status}")
        st.write(detail)

st.subheader("Practice decision")

choice = st.radio(
    "Which action preserves evaluation integrity?",
    [
        "Tune the threshold after seeing external outcomes",
        "Repeat external runs until metrics stabilize",
        "Freeze development choices before one external run",
    ],
    index=None,
)

if choice is not None:
    if choice.startswith("Freeze"):
        st.success("Correct: freeze development choices first.")
    else:
        st.error("That action would compromise the evaluation boundary.")

footer()