"""Data loading and preprocessing for MPLADS data."""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from datetime import date

BASE_DIR = Path(__file__).parent.parent


def load_ml_ready_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the ML-ready Lok Sabha and Rajya Sabha datasets."""
    ml_ready_dir = BASE_DIR / "data" / "ml_ready"
    
    lok_df = pd.read_csv(ml_ready_dir / "MPLADS_Lok_Sabha_ml_ready.csv")
    rajya_df = pd.read_csv(ml_ready_dir / "MPLADS_Rajya_Sabha_ml_ready.csv")
    
    return lok_df, rajya_df


def combine_datasets(lok_df: pd.DataFrame, rajya_df: pd.DataFrame) -> pd.DataFrame:
    """Combine Lok Sabha and Rajya Sabha datasets."""
    combined = pd.concat([lok_df, rajya_df], ignore_index=True)
    
    # Create a unique project ID
    combined["project_id"] = combined.apply(
        lambda x: f"{'R' if 'rajya' in str(x['house']).casefold() else 'L'}{x.name:05d}", axis=1
    )
    
    return combined


def load_combined_data() -> pd.DataFrame:
    """Load and combine both datasets."""
    lok_df, rajya_df = load_ml_ready_data()
    combined = combine_datasets(lok_df, rajya_df)
    return add_prototype_monitoring_fields(combined)


def add_prototype_monitoring_fields(df: pd.DataFrame, current_date=None) -> pd.DataFrame:
    """Add explicitly simulated financial/progress fields without changing source data.

    The available source files contain allocations only. Demonstration expenditure
    and lifecycle values are deterministic, visibly labelled prototype fields.
    """
    result = df.copy()
    today = pd.Timestamp(current_date or date.today()).normalize()
    allocation_source = result["allocated_amount"] if "allocated_amount" in result else pd.Series(0, index=result.index)
    allocation = pd.to_numeric(allocation_source, errors="coerce").fillna(0).clip(lower=0)
    positions = np.arange(len(result), dtype=float)
    # Stable demo ratios: 12%-92% of released funds, no randomness or raw-file edits.
    released_ratio = 0.72 + ((positions * 17) % 25) / 100
    utilization_ratio = 0.08 + ((positions * 13) % 85) / 100
    result["allocated_amount"] = allocation
    result["released_amount"] = allocation * released_ratio
    result["expenditure_amount"] = result["released_amount"] * utilization_ratio
    result["remaining_amount"] = (result["released_amount"] - result["expenditure_amount"]).clip(lower=0)
    result["utilization_percentage"] = np.where(
        result["released_amount"] > 0,
        result["expenditure_amount"] / result["released_amount"] * 100,
        0.0,
    )
    result["utilization_percentage"] = pd.Series(result["utilization_percentage"], index=result.index).fillna(0)

    # Staggered demo lifecycle dates span 180–540 days and end 20–240 days ago.
    durations = 180 + (positions.astype(int) * 37 % 361)
    elapsed = 20 + (positions.astype(int) * 19 % 221)
    elapsed = np.minimum(elapsed, durations + 120)  # allow overdue projects, never future starts
    result["project_start_date"] = [today - pd.Timedelta(days=int(d + e)) for d, e in zip(durations, elapsed)]
    result["expected_completion_date"] = [s + pd.Timedelta(days=int(d)) for s, d in zip(result["project_start_date"], durations)]
    result["current_date"] = today
    result["project_progress_percentage"] = np.minimum(100, result["utilization_percentage"] * (0.85 + (positions % 20) / 100))
    total_days = (result["expected_completion_date"] - result["project_start_date"]).dt.days.replace(0, np.nan)
    elapsed_days = (today - result["project_start_date"]).dt.days.clip(lower=0)
    result["expected_progress_percentage"] = (elapsed_days / total_days * 100).clip(0, 100).fillna(0)
    result["progress_gap_percentage"] = (result["expected_progress_percentage"] - result["project_progress_percentage"]).clip(lower=0)
    result["progress_status"] = np.select(
        [result["progress_gap_percentage"] > 25, result["progress_gap_percentage"] > 10],
        ["DELAY RISK", "AT RISK"], default="ON TRACK",
    )
    result["monitoring_data_source"] = "SIMULATED PROTOTYPE DATA"
    return result


def get_financial_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract and prepare financial features for ML models."""
    features = df.copy()
    
    # Ensure allocated_amount is numeric
    features["allocated_amount"] = pd.to_numeric(
        features["allocated_amount"], errors="coerce"
    )
    
    # Fill missing values
    features["allocated_amount"] = features["allocated_amount"].fillna(
        features["allocated_amount"].median()
    )
    
    return features


def prepare_for_anomaly_detection(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for Isolation Forest anomaly detection."""
    features = df.copy()
    
    # Select numeric features for anomaly detection
    numeric_cols = ["allocated_amount"]
    
    # Add engineered features if available
    if "allocation_zscore" in features.columns:
        numeric_cols.append("allocation_zscore")
    
    # Create additional derived features
    features["allocated_amount"] = pd.to_numeric(features["allocated_amount"], errors="coerce").fillna(0)
    features["allocation_log"] = np.log1p(features["allocated_amount"])
    
    # State-normalized allocation
    if "state_avg_allocation" in features.columns:
        state_average = pd.to_numeric(features["state_avg_allocation"], errors="coerce").replace(0, np.nan)
        features["allocation_vs_state"] = (features["allocated_amount"] / state_average).replace([np.inf, -np.inf], np.nan).fillna(0)
        numeric_cols.append("allocation_vs_state")
    
    return features, numeric_cols


if __name__ == "__main__":
    # Test loading
    lok, rajya = load_ml_ready_data()
    print(f"Lok Sabha: {lok.shape}")
    print(f"Rajya Sabha: {rajya.shape}")
    
    combined = combine_datasets(lok, rajya)
    print(f"Combined: {combined.shape}")
