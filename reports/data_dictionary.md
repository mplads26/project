# MPLADS Data Dictionary

## Project
AI-Powered System for Detecting Anomalies, Fraud, and Inefficiencies in MPLADS Scheme Implementation

---

# 1. Lok Sabha Dataset

File: `MPLADS_Lok_Sabha_ml_ready.csv`

| Column | Description |
|---|---|
| `sr_no` | Original serial number of the record |
| `state` | State or Union Territory |
| `mp_name` | Name of the Member of Parliament |
| `constituency` | Lok Sabha constituency |
| `allocated_amount` | Allocation amount in Indian Rupees |
| `house` | Parliamentary house identifier: Lok Sabha |
| `allocation_vs_mean` | Difference between the MP's allocation and the overall mean allocation |
| `allocation_pct_from_mean` | Percentage difference from the overall mean allocation |
| `state_avg_allocation` | Average allocation of records within the same state |
| `allocation_vs_state_avg` | Difference between the MP's allocation and their state's average allocation |
| `allocation_pct_from_state_avg` | Percentage difference from the state's average allocation |
| `allocation_zscore` | Standardized score showing how unusual the allocation is compared with the dataset distribution |
| `zscore_anomaly` | True if the absolute Z-score is greater than 3; otherwise False |
| `risk_level` | Risk category: Low, Medium, High, or Unknown |
| `anomaly_reason` | Human-readable explanation of the allocation risk or anomaly |

---

# 2. Rajya Sabha Dataset

File: `MPLADS_Rajya_Sabha_ml_ready.csv`

| Column | Description |
|---|---|
| `sr_no` | Original serial number of the record |
| `state` | State or Union Territory |
| `mp_name` | Name of the Member of Parliament |
| `member_type` | Type of Rajya Sabha membership, such as Elected MP or Nominated MP |
| `allocated_amount` | Allocation amount in Indian Rupees |
| `house` | Parliamentary house identifier: Rajya Sabha |
| `allocation_vs_mean` | Difference between the MP's allocation and the overall mean allocation |
| `allocation_pct_from_mean` | Percentage difference from the overall mean allocation |
| `state_avg_allocation` | Average allocation of records within the same state |
| `allocation_vs_state_avg` | Difference between the MP's allocation and their state's average allocation |
| `allocation_pct_from_state_avg` | Percentage difference from the state's average allocation |
| `allocation_zscore` | Standardized score showing how unusual the allocation is compared with the dataset distribution |
| `zscore_anomaly` | True if the absolute Z-score is greater than 3; otherwise False |
| `risk_level` | Risk category: Low, Medium, High, or Unknown |
| `anomaly_reason` | Human-readable explanation of the allocation risk or anomaly |

---

# Notes for AI/ML Team

- Use `allocated_amount` and the engineered numerical features as inputs for anomaly detection experiments.
- `allocation_zscore` and `zscore_anomaly` are baseline statistical anomaly indicators created during data engineering.
- `risk_level` and `anomaly_reason` are derived from the Z-score and are useful for explainability and dashboard display.
- One Lok Sabha record has a missing `allocated_amount`; handle or exclude this record before training models that require complete numerical inputs.
- Raw source files are available in `data/raw/`.
- Cleaned intermediate datasets are available in `data/processed/`.
- Final feature-engineered datasets are available in `data/ml_ready/`.