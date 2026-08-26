from pathlib import Path


def source(name):
    return Path(name).read_text(encoding="utf-8")


def test_framework_is_session_aware():
    text = source("pages/1_Framework.py")
    assert "ensure_workspace" in text
    assert "Current browser-session workspace" in text


def test_governance_has_downloadable_receipt():
    text = source("pages/6_Evaluation_Governance.py")
    assert "Download governance receipt JSON" in text
    assert "camelyon17_accessed" in text


def test_reproducibility_has_live_environment():
    text = source("pages/7_Reproducibility.py")
    assert "torch.__version__" in text
    assert "Download reproducibility receipt JSON" in text


def test_collection_page_auto_generates_grid():
    text = source("pages/3_Patch_Collection_Analysis.py")
    assert 'workspace["coordinate_source"] = "generated_qa_grid"' in text
