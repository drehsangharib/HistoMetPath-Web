import io
import json
import zipfile
import pytest
from histometpath_web.spatial_v31_contract import SpatialV31ContractError, create_job_spec, job_spec_bytes, validate_result_bundle

def receipt(**updates):
    value={
        "coordinates_byte_reproducible": True, "fractions_byte_reproducible": True,
        "restart_reuse_validated": True, "corrupt_copy_rejected": True, "passed": True,
        "restart_wsi_files_opened": 0, "restart_region_reads": 0, "saved_tile_pixels": 0,
        "validation_arrays_opened": 0, "protected_test_arrays_opened": 0,
        "camelyon17_files_opened": 0, "annotations_opened": 0,
        "training_operations": 0, "evaluation_operations": 0,
        "run1_selected_coordinate_count": 300, "run2_selected_coordinate_count": 300,
    }
    value.update(updates); return value

def bundle(value=None, name="root/SPATIAL_V31_MEGA2_FIX2A_QUALIFICATION_RECEIPT.json"):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name,json.dumps(receipt() if value is None else value))
    return stream.getvalue()

def test_job_is_research_only_and_serializable():
    spec=create_job_spec("normal_027","/authorized/normal_027.tif","normal")
    assert spec["coordinate_count"]==300 and spec["clinical_use"] is False
    assert json.loads(job_spec_bytes(spec))["slide_id"]=="normal_027"

def test_job_rejects_remote_url_and_bad_slide():
    with pytest.raises(SpatialV31ContractError,match="Remote"): create_job_spec("normal_027","https://example.test/a.tif","normal")
    with pytest.raises(SpatialV31ContractError,match="characters"): create_job_spec("../test_001","x","normal")

def test_valid_bundle_passes():
    result=validate_result_bundle(bundle())
    assert result["contract_pass"] is True and len(result["bundle_sha256"])==64

def test_bundle_rejects_protected_access():
    with pytest.raises(SpatialV31ContractError,match="zero-access"):
        validate_result_bundle(bundle(receipt(protected_test_arrays_opened=1)))

def test_bundle_rejects_bad_coordinate_count():
    with pytest.raises(SpatialV31ContractError,match="300 coordinates"):
        validate_result_bundle(bundle(receipt(run2_selected_coordinate_count=299)))

def test_bundle_rejects_path_traversal():
    with pytest.raises(SpatialV31ContractError,match="Unsafe ZIP"):
        validate_result_bundle(bundle(name="../SPATIAL_V31_MEGA2_FIX2A_QUALIFICATION_RECEIPT.json"))
