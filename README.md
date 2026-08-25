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
