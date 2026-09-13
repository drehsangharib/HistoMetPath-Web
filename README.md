# HistoMetPath Web

Synthetic-only Streamlit companion to [HistoMetPath](https://github.com/drehsangharib/HistoMetPath).

## Safety boundary

- No CAMELYON17 access
- No external execution token or lock
- No WSI upload
- No patient data
- No clinical use

## Local run

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q
streamlit run app.py
```

## Deploy

Deploy `app.py` from the `main` branch through Streamlit Community Cloud and select Python 3.11 in Advanced settings.
## Spatial-v3.1 WSI workflow
The web app does not upload or open whole-slide images. The WSI Workflow page creates a research-only JSON job for authorized local or worker execution and validates returned Spatial-v3.1 qualification receipts. Coordinate generation is CPU-based; bulk embedding extraction may use a GPU. Direct multi-gigabyte public WSI upload remains unsupported.
