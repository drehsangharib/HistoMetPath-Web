from pathlib import Path


PAGES = Path("pages")


def source(name: str) -> str:
    path = PAGES / name
    assert path.is_file(), f"Expected page is missing: {path}"
    return path.read_text(encoding="utf-8")


def test_analyze_page_supports_all_input_modes_and_regional_state():
    text = source("2_Analyze.py")
    assert '"Single patch"' in text
    assert '"Patch collection"' in text
    assert '"Large image"' in text
    assert 'workspace["regional"]' in text
    assert 'large_image_authentic_pixel_coordinates' in text


def test_results_overview_is_distinct_and_session_aware():
    text = source("3_Results_Overview.py")
    assert "Results Overview" in text
    assert "Score distribution" in text
    assert "Near-threshold observations" in text
    assert "Large-image coverage summary" in text
    assert "ensure_workspace" in text


def test_analysis_record_combines_provenance_and_governance():
    text = source("6_Analysis_Record.py")
    assert "Technical provenance" in text
    assert "Interpretation boundaries" in text
    assert "protected_evaluation_accessed" in text
    assert "Download analysis record JSON" in text


def test_streamlined_pages_replace_obsolete_pages():
    expected = {
        "2_Analyze.py",
        "3_Results_Overview.py",
        "4_Spatial_Analysis.py",
        "5_Patch_Gallery.py",
        "6_Analysis_Record.py",
        "7_About_Limitations.py",
    }
    obsolete = {
        "1_Framework.py",
        "2_Upload_and_Analyze.py",
        "3_Patch_Collection_Analysis.py",
        "4_Spatial_Patch_Map.py",
        "5_Patch_Set_Summaries.py",
        "6_Evaluation_Governance.py",
        "7_Reproducibility.py",
    }
    assert all((PAGES / name).is_file() for name in expected)
    assert all(not (PAGES / name).exists() for name in obsolete)