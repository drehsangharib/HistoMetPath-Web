import json
import streamlit as st
from histometpath_web.spatial_v31_contract import (
    SpatialV31ContractError, create_job_spec, job_spec_bytes, validate_result_bundle,
)
from histometpath_web.ui import configure, footer

configure("WSI Workflow")
st.title("Spatial-v3.1 WSI Workflow")
st.caption("Create a controlled local-worker job and validate its returned research receipt")
st.warning("Whole-slide images are not uploaded to or opened by this web application. WSI execution remains local or worker-based. This workflow is research-only and is not a clinical service.")

create_tab, validate_tab = st.tabs(["Create worker job", "Validate result bundle"])
with create_tab:
    st.subheader("Job specification")
    slide_id = st.text_input("Slide identifier", placeholder="normal_027")
    source_locator = st.text_input("Authorized local/worker WSI locator", placeholder="/authorized/training/normal_027.tif")
    label = st.selectbox("Expected research label", ["unknown", "normal", "tumor"])
    st.info("The locator is descriptive job metadata. The browser does not read, verify, or transmit the WSI itself.")
    if st.button("Create Spatial-v3.1 job", type="primary"):
        try:
            spec = create_job_spec(slide_id, source_locator, label)
            st.success("Research-only worker job created.")
            st.json(spec)
            st.download_button("Download job JSON", job_spec_bytes(spec), f"{spec['slide_id']}_spatial_v31_job.json", "application/json", use_container_width=True)
        except SpatialV31ContractError as error:
            st.error(str(error))

with validate_tab:
    st.subheader("Returned qualification bundle")
    upload = st.file_uploader("Upload a Spatial-v3.1 result ZIP, maximum 10 MB", type=["zip"], key="spatial_v31_result")
    if upload and st.button("Validate Spatial-v3.1 result", type="primary"):
        try:
            validation = validate_result_bundle(upload.getvalue())
            st.success("The result bundle passes the browser-side Spatial-v3.1 receipt contract.")
            st.metric("Bundle size", f"{validation['bundle_size_bytes']:,} bytes")
            st.code(validation["bundle_sha256"], language=None)
            st.json(validation["receipt"])
            st.download_button("Download validation JSON", json.dumps(validation, indent=2), "spatial_v31_bundle_validation.json", "application/json", use_container_width=True)
        except SpatialV31ContractError as error:
            st.error(str(error))

st.info("Receipt validation confirms implementation and access-control fields in the submitted evidence. It does not authenticate specimen identity or establish diagnostic performance.")
footer()
