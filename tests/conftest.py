from pathlib import Path
import os
import pytest


@pytest.fixture(scope="session")
def validated_model_path() -> Path:
    configured = os.environ.get("HISTOMETPATH_MODEL_PATH")
    if not configured:
        pytest.skip("HISTOMETPATH_MODEL_PATH is required for acquisition integration tests.")
    path = Path(configured).resolve()
    if not path.is_file():
        pytest.fail(f"Validated model artifact missing: {path}")
    return path
