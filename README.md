# MPLADS AI — Intelligent Risk & Monitoring Prototype

This folder contains the runnable MPLADS AI prototype for Smart India Hackathon 2026, Problem Statement 26102. It extends the existing allocation pipeline with explainable monitoring and human investigation support.

**Prototype disclaimer:** Monitoring thresholds and simulated expenditure/lifecycle fields are for demonstration and are not official Government of India rules or source records. An anomaly or similarity signal is not a finding of fraud.

See [README_PROTOTYPE.md](README_PROTOTYPE.md) for setup, features, API endpoints, data assumptions, risk calculations, testing commands, and PDF report usage.

Quick start from this folder:

```powershell
pip install -r requirements.txt
python -m uvicorn mplads.backend.main:app --port 8000
```

In another terminal:

```powershell
python -m streamlit run mplads/dashboard/app.py --server.port 8502
```

Open `http://localhost:8502`.
