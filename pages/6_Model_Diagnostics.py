from pathlib import Path
import io
import json
import platform

import pandas as pd
from PIL import Image
import streamlit as st
import torch

from histometpath_web.inference import (
    EXPECTED_MODEL_SHA256, HISTORICAL_THRESHOLD, file_sha256, load_inference_model,
)
from histometpath_web.model_acquisition import acquire_model
from histometpath_web.model_diagnostics import (
    append_diagnostic_columns, duplicate_summary, image_morphology_metrics,
    model_contract_receipt, score_diagnostics,
)
from histometpath_web.ui import configure, footer
from histometpath_web.workspace import collection_frame, ensure_workspace

configure('Model Diagnostics')
st.title('Model Diagnostics')
st.caption('Research-only domain, quality, saturation, and model-contract diagnostics')
workspace = ensure_workspace(st.session_state)
records = workspace.get('collection') or []

st.warning('These outputs describe model behavior and image characteristics. They do not establish diagnosis, accuracy, calibration, tumor boundaries, or malignant area.')

with st.expander('Specimen metadata and provenance', expanded=True):
    c1, c2, c3 = st.columns(3)
    tissue_type = c1.text_input('Tissue type, if known')
    stain = c2.text_input('Stain', value='H&E')
    scanner = c3.text_input('Scanner or acquisition system')
    c4, c5, c6 = st.columns(3)
    magnification = c4.text_input('Magnification, if known')
    mpp = c5.text_input('Microns per pixel, if known')
    provenance = c6.selectbox('Provenance status', ['Unknown', 'Authorized/public with known source', 'Verified research cohort'])
    workspace['diagnostic_metadata'] = {
        'tissue_type': tissue_type, 'stain': stain, 'scanner': scanner,
        'magnification': magnification, 'microns_per_pixel': mpp,
        'provenance_status': provenance,
    }

if not records:
    st.info('Analyze a patch collection or large image first. Diagnostics will use the shared session results.')
    footer(); st.stop()

frame = append_diagnostic_columns(collection_frame(records))
score_summary = score_diagnostics(frame)
duplicates = duplicate_summary(frame)

st.subheader('Score saturation and threshold distance')
a, b, c, d = st.columns(4)
a.metric('Valid scores', score_summary['valid_scores'])
b.metric('Scores >= 0.95', f"{100 * (score_summary['fraction_at_least_0_95'] or 0):.1f}%")
c.metric('Scores >= 0.99', f"{100 * (score_summary['fraction_at_least_0_99'] or 0):.1f}%")
d.metric('Near threshold', f"{100 * (score_summary['near_threshold_fraction'] or 0):.1f}%")
if score_summary.get('saturation_warning'):
    st.warning('Score saturation detected. This can reflect strong model response, domain shift, preprocessing effects, or spurious correlations. It is not proof of malignant tissue.')

st.dataframe(frame.drop(columns=['bytes'], errors='ignore'), use_container_width=True, hide_index=True)

st.subheader('Input integrity')
e, f, g = st.columns(3)
e.metric('Unique hashes', duplicates['unique_hashes'])
f.metric('Duplicate records', duplicates['duplicate_records'])
g.metric('Duplicate groups', duplicates['duplicate_groups'])
if duplicates['duplicate_records']:
    st.warning('Duplicate image hashes were found. Repeated patches can distort collection-level summaries.')

st.subheader('Available image morphology')
morphology_rows = []
regional = workspace.get('regional')
if regional and regional.get('image_bytes'):
    source = Image.open(io.BytesIO(regional['image_bytes'])).convert('RGB')
    for row in regional.get('tiles', [])[:1000]:
        crop = source.crop((int(row['x']), int(row['y']), int(row['x']) + 96, int(row['y']) + 96))
        morphology_rows.append({'filename': row['filename'], **image_morphology_metrics(crop).to_dict()})
else:
    st.info('Morphology metrics are available automatically for large-image tiles. Patch collections currently retain hashes and inference records but not image bytes.')

if morphology_rows:
    morphology = pd.DataFrame(morphology_rows)
    st.dataframe(morphology, use_container_width=True, hide_index=True)
    st.caption('Nuclear-like fraction, H&E-like purple fraction, tissue fraction, and blur proxy are deterministic descriptive proxies, not cell counts, stain deconvolution, or pathology annotations.')

st.subheader('Frozen model contract')
@st.cache_resource
def contract_data():
    local = Path(__file__).resolve().parents[1] / 'local_model_artifacts' / 'histometpath_resnet18_patch_state_dict.pt'
    path = acquire_model(local_override=local if local.is_file() else None)
    _, payload = load_inference_model(path)
    receipt = model_contract_receipt(
        expected_sha256=EXPECTED_MODEL_SHA256,
        observed_sha256=file_sha256(Path(path)),
        code_threshold=HISTORICAL_THRESHOLD,
        artifact_threshold=float(payload['historical_threshold']),
        architecture=str(payload['architecture']),
        input_size=payload['input_size'],
    )
    receipt.update({'python': platform.python_version(), 'torch': torch.__version__, 'device': 'cpu', 'model_mode': 'eval'})
    return receipt
receipt = contract_data()
st.json(receipt)
if not receipt['contract_pass']:
    st.error('Frozen model contract failed. Do not interpret inference results until the mismatch is resolved.')
else:
    st.success('Frozen model hash, architecture, input size, and threshold contract agree.')

export = {
    'interpretation_boundary': 'Research-only diagnostics; not diagnosis, calibration, segmentation, or accuracy.',
    'metadata': workspace.get('diagnostic_metadata', {}),
    'score_summary': score_summary,
    'duplicates': duplicates,
    'model_contract': receipt,
}
st.download_button('Download diagnostics receipt', json.dumps(export, indent=2), 'histometpath_model_diagnostics_receipt.json', 'application/json', use_container_width=True)
footer()
