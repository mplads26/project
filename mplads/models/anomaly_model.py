"""Anomaly detection using Isolation Forest."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List, Dict


class AnomalyDetector:
    """Detect anomalies in MPLADS data using Isolation Forest."""
    
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        """
        Initialize the anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (0-1)
            random_state: Random seed for reproducibility
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        
    def _create_features(self, df: pd.DataFrame) -> np.ndarray:
        """Create feature matrix for anomaly detection."""
        features = df.copy()
        
        # Ensure numeric
        features["allocated_amount"] = pd.to_numeric(
            features["allocated_amount"], errors="coerce"
        ).fillna(features["allocated_amount"].median())
        
        # Log transform for better distribution
        features["log_allocation"] = np.log1p(features["allocated_amount"])
        
        # Use z-score if available
        if "allocation_zscore" in features.columns:
            features["zscore"] = features["allocation_zscore"].fillna(0)
        else:
            # Compute z-score ourselves
            mean_alloc = features["allocated_amount"].mean()
            std_alloc = features["allocated_amount"].std()
            features["zscore"] = (
                (features["allocated_amount"] - mean_alloc) / std_alloc
            )
        
        # State-normalized ratio
        if "state_avg_allocation" in features.columns:
            features["state_ratio"] = (
                features["allocated_amount"] / 
                features["state_avg_allocation"].replace(0, 1)
            ).fillna(1)
        else:
            features["state_ratio"] = 1.0
        
        # Select features
        feature_cols = ["log_allocation", "zscore", "state_ratio"]
        self.feature_names = feature_cols
        
        return features[feature_cols].values
    
    def fit(self, df: pd.DataFrame) -> "AnomalyDetector":
        """Train the Isolation Forest model."""
        X = self._create_features(df)
        X_scaled = self.scaler.fit_transform(X)
        
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
            max_samples="auto"
        )
        self.model.fit(X_scaled)
        
        return self
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Predict anomalies for the dataset."""
        X = self._create_features(df)
        X_scaled = self.scaler.transform(X)
        
        # Get anomaly scores (-1 for anomaly, 1 for normal)
        predictions = self.model.predict(X_scaled)
        
        # Get anomaly scores (lower = more anomalous)
        anomaly_scores = self.model.decision_function(X_scaled)
        
        # Convert to 0-100 scale (higher = more anomalous)
        # Normalize the scores
        min_score = anomaly_scores.min()
        max_score = anomaly_scores.max()
        if max_score - min_score > 0:
            normalized_scores = (anomaly_scores - min_score) / (max_score - min_score)
        else:
            normalized_scores = np.zeros_like(anomaly_scores)
        
        # Invert so higher = more anomalous
        anomaly_risk = (1 - normalized_scores) * 100
        
        result = df.copy()
        result["anomaly_prediction"] = predictions  # -1 = anomaly, 1 = normal
        result["anomaly_score"] = np.round(anomaly_risk, 2)
        result["is_anomaly"] = predictions == -1
        
        return result
    
    def explain_anomaly(self, row: pd.Series) -> List[str]:
        """Explain why a project was flagged as anomalous."""
        reasons = []
        
        # Check allocation amount
        if row.get("anomaly_score", 0) > 70:
            alloc = row.get("allocated_amount", 0)
            if alloc > 50000000:  # > 5 Cr
                reasons.append("Extremely high allocation amount")
            elif alloc < 1000000:  # < 10 Lakh
                reasons.append("Unusually low allocation amount")
        
        # Check z-score
        zscore = row.get("allocation_zscore", 0)
        if abs(zscore) > 3:
            reasons.append(f"Allocation is {abs(zscore):.1f} standard deviations from mean")
        
        # Check state ratio
        state_ratio = row.get("allocation_vs_state_avg", 0)
        if state_ratio and abs(state_ratio) > 10000000:
            reasons.append("Allocation significantly differs from state average")
        
        if not reasons:
            reasons.append("Unusual pattern detected in financial data")
            
        return reasons


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    """Convenience function to detect anomalies."""
    detector = AnomalyDetector(contamination=contamination)
    detector.fit(df)
    return detector.predict(df)


if __name__ == "__main__":
    # Test
    from mplads.data_loader import load_combined_data
    
    df = load_combined_data()
    result = detect_anomalies(df)
    
    anomalies = result[result["is_anomaly"] == True]
    print(f"Detected {len(anomalies)} anomalies out of {len(result)} projects")