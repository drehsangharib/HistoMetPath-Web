from pathlib import Path
import json

import streamlit as st

from histometpath_web.model_acquisition import ModelAcquisitionError, acquire_model
from histometpath_web.inference import (
    EXPECTED_MODEL_SHA256,
    ImageValidationError,
    decode_uploaded_image,
    load_inference_model,
    predict_image,
)
from histometpath_web.ui import configure, footer

configure("Upload & Analyze")
st.title("Upload & Analyze")
st.caption("Patch-level breast histopathology research inference")

st.warning(
    "Research demonstration only. The score is not a diagnosis, a patient-level result, "
    "or a calibrated probability of cancer. Upload only de-identified images that you are authorized to use."
)

LOCAL_MODEL_PATH = Path(__file__).resolve().parents[1] / "local_model_artifacts" / "histometpath_resnet18_patch_state_dict.pt"

with st.expander("Validated model contract", expanded=False):
    st.code(
        "Architecture: ResNet-18\n"
        "Input: RGB image resized to 96 x 96\n"
        "Output: sigmoid tumor-associated research score\n"
        "Historical threshold: 0.5\n"
        f"Artifact SHA-256: {EXPECTED_MODEL_SHA256}"
    )

uploaded = st.file_uploader(
    "Upload one PNG or JPEG histopathology patch",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=False,
    help="Maximum 10 MB and 16.8 megapixels. PCAM-like breast histopathology patches are the validated use case.",
)

if uploaded is None:
    st.info("Choose a PNG or JPEG image to begin local research-model analysis.")
else:
    try:
        image = decode_uploaded_image(uploaded)
        st.image(image, caption=f"Uploaded image: {image.width} x {image.height}, mode {image.mode}", width="stretch")

        with st.spinner("Acquiring and verifying the frozen model..."):
            model_path = acquire_model(
                local_override=LOCAL_MODEL_PATH if LOCAL_MODEL_PATH.is_file() else None
            )
        with st.spinner("Running frozen HistoMetPath patch inference..."):
            model, _metadata = load_inference_model(model_path)
            result = predict_image(image, model)

            col1, col2 = st.columns(2)
            col1.metric("Tumor-associated research score", f"{result.score:.4f}")
            col2.metric("Historical threshold", f"{result.historical_threshold:.2f}")

            if result.threshold_prediction == 1:
                st.warning(result.threshold_interpretation)
            else:
                st.success(result.threshold_interpretation)

            st.write(
                "The frozen patch classifier detected image features with the score shown above. "
                "A score above 0.5 means the model output exceeded its historical patch-level threshold. "
                "This does not establish a diagnosis, and a below-threshold score does not prove benign tissue."
            )

            report = {
                "schema_version": "1.0",
                "analysis_type": "HistoMetPath patch-level research inference",
                "result": result.to_dict(),
                "limitations": [
                    "Not a clinical diagnosis or calibrated cancer-risk probability.",
                    "Validated for PCAM-compatible breast histopathology patches, not arbitrary images.",
                    "A single patch is not a whole-slide or patient-level result.",
                ],
            }
            st.download_button(
                "Download research result JSON",
                data=json.dumps(report, indent=2),
                file_name="histometpath_patch_result.json",
                mime="application/json",
            )
    except (ImageValidationError, ModelAcquisitionError) as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Inference could not be completed: {error}")

footer()
