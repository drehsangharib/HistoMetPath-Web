"""Checksum-verified acquisition of the frozen HistoMetPath model artifact."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from urllib.request import Request, urlopen

MODEL_FILENAME = "histometpath_resnet18_patch_state_dict.pt"
EXPECTED_MODEL_SHA256 = "d01611d5e370ad14cb4eb052ff1de31b6650780647f64107487a22eceba5cf90"
EXPECTED_MODEL_SIZE = 45_839_941
DEFAULT_MODEL_URL = (
    "https://github.com/drehsangharib/HistoMetPath-Web/releases/download/"
    "model-v1/histometpath_resnet18_patch_state_dict.pt"
)
CHUNK_SIZE = 1024 * 1024
MAX_DOWNLOAD_BYTES = EXPECTED_MODEL_SIZE + 1024


class ModelAcquisitionError(RuntimeError):
    """Raised when the model cannot be acquired and verified safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_model_file(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_file():
        raise ModelAcquisitionError(f"Model artifact not found: {candidate}")
    size = candidate.stat().st_size
    if size != EXPECTED_MODEL_SIZE:
        raise ModelAcquisitionError(
            f"Model size mismatch: expected {EXPECTED_MODEL_SIZE}, found {size}."
        )
    checksum = sha256_file(candidate)
    if checksum != EXPECTED_MODEL_SHA256:
        raise ModelAcquisitionError("Model SHA-256 verification failed.")
    return candidate


def default_cache_path() -> Path:
    configured = os.getenv("HISTOMETPATH_MODEL_CACHE")
    if configured:
        return Path(configured).expanduser().resolve() / MODEL_FILENAME
    return Path.home() / ".cache" / "histometpath-web" / MODEL_FILENAME


def acquire_model(
    *,
    cache_path: str | Path | None = None,
    model_url: str | None = None,
    local_override: str | Path | None = None,
    timeout_seconds: float = 120.0,
) -> Path:
    override = local_override or os.getenv("HISTOMETPATH_MODEL_PATH")
    if override:
        return verify_model_file(override)

    destination = Path(cache_path) if cache_path else default_cache_path()
    destination = destination.expanduser().resolve()

    if destination.exists():
        try:
            return verify_model_file(destination)
        except ModelAcquisitionError:
            destination.unlink(missing_ok=True)

    url = model_url or os.getenv("HISTOMETPATH_MODEL_URL") or DEFAULT_MODEL_URL
    if not url.lower().startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
        raise ModelAcquisitionError("Model URL must use HTTPS, except localhost tests.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{MODEL_FILENAME}.", suffix=".part",
            dir=destination.parent, delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            request = Request(url, headers={"User-Agent": "HistoMetPath-Web/0.2"})
            total = 0
            with urlopen(request, timeout=timeout_seconds) as response:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ModelAcquisitionError("Model download exceeded the safety limit.")
                    temporary.write(chunk)
            temporary.flush()
            os.fsync(temporary.fileno())

        verify_model_file(temporary_path)
        os.replace(temporary_path, destination)
        temporary_path = None
        return verify_model_file(destination)
    except ModelAcquisitionError:
        raise
    except Exception as error:
        raise ModelAcquisitionError(f"Model acquisition failed: {error}") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
