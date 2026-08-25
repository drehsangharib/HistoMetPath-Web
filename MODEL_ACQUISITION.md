# Verified model acquisition

HistoMetPath-Web obtains the frozen inference artifact from the `model-v1` GitHub Release when no local development override exists.

Safety contract:
- exact size: `45,839,941` bytes
- exact SHA-256: `d01611d5e370ad14cb4eb052ff1de31b6650780647f64107487a22eceba5cf90`
- temporary `.part` download
- maximum-size guard
- verification before atomic cache promotion
- `torch.load(..., weights_only=True)` after verification

Local development may set `HISTOMETPATH_MODEL_PATH`. Deployment may set `HISTOMETPATH_MODEL_URL` to override the default release URL.
