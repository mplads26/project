# MPLADS AI — Risk Monitoring Prototype

Smart India Hackathon 2026 · Problem Statement 26102

This existing local prototype combines Lok Sabha and Rajya Sabha MPLADS allocation records, anomaly detection, rule checks, explainable risk scoring, similarity screening, FastAPI, and Streamlit. It supports human investigation; an anomaly is not a finding of fraud.

> This is a prototype monitoring system. The monitoring thresholds and simulated fields are for demonstration and are not official Government of India rules.

## Features

- Source allocation data remains in `data/raw/` and `data/ml_ready/`; files are never rewritten by runtime monitoring features.
- Isolation Forest, existing allocation compliance checks, financial risk scoring, and similarity screening remain in place.
- Expenditure fields (`released_amount`, `expenditure_amount`, `remaining_amount`, `utilization_percentage`) and progress dates/status are generated deterministically at runtime because the supplied dataset does not contain project expenditure or lifecycle information. They carry `monitoring_data_source=SIMULATED PROTOTYPE DATA`.
- Prototype monitoring thresholds: utilization below 25% gives a warning, below 10% is critical, high allocation with low utilization is a risk indicator; progress gap <=10 pp is ON TRACK, >10–25 pp AT RISK, >25 pp DELAY RISK.
- The original 35/35/30 anomaly/compliance/financial composite and risk bands are preserved. Utilization and delay risk are additional breakdown/health signals, not retroactively blended into historic overall scores.
- Similarity means potential similarity only and always requires human verification.
- Local PDF investigation reports include score, reasons, breakdown, simulated financial/progress values, similarity summary, review status/comment, and generation timestamp.
- Review status and comments are held in memory for the running API process; restarting loses them.

## Run locally

Python 3.11+ is recommended. From the application directory (`C:\sem 5\sih\MPLADS\MPLADS`):

```powershell
pip install -r requirements.txt
python -m uvicorn mplads.backend.main:app --port 8000
```

In a second terminal:

```powershell
cd C:\sem 5\sih\MPLADS\MPLADS
python -m streamlit run mplads/dashboard/app.py --server.port 8502
```

Open `http://localhost:8502`. API docs are at `http://localhost:8000/docs`. For a one-command launcher, see `run_demo.py`.

## Dashboard sections

Overview, Risk Alerts (filter by risk/type/state), Projects, Project Investigation, State Analysis, Project Health, and Reports. Details include risk reasons/breakdown, utilization/progress charts, similar-project metadata, review workflow, lifecycle timeline, and PDF download.

## API

Backward-compatible existing endpoints: `GET /`, `/dashboard/summary`, `/projects`, `/projects/{id}`, `/alerts`, `/states`, `/risk/distribution`.

Added endpoints:

- `GET /projects/{id}/health` — separate health indicators; does not replace overall risk.
- `GET /projects/{id}/report` — PDF download.
- `GET /states/{state}/summary` — project/risk/allocation summary.
- `PUT /projects/{id}/review` — in-memory human review status and comment; JSON body `{ "status": "UNDER INVESTIGATION", "comment": "..." }`.
- `GET /alerts?risk_level=HIGH&alert_type=DELAY%20RISK&state=...` — alert filtering.

## Risk calculations and data limits

The preserved score is `0.35 * anomaly_risk + 0.35 * compliance_risk + 0.30 * financial_risk`, classified HIGH at 70+, MEDIUM at 40–69.99, LOW below 40. Utilization risk and delay risk are shown separately in explanations and health views. Prototype rules do not claim official policy status.

Real source fields are distinguishable from calculated allocation risk fields and runtime demo fields. No expenditure, released amount, start/completion date, or actual progress fields existed in the supplied source CSVs; all such fields are simulated, deterministic, and explicitly labelled. Do not use them as audited financial or project status data.

## Tests

```powershell
python -m unittest test_monitoring_features.py
python test_imports.py
python test_ml_pipeline.py
```

PDF output uses ReportLab. Other dependencies are listed in `requirements.txt`. No database, login, or cloud services are required.
