"""Risk engine combining all signals into final risk score."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from mplads.models.anomaly_model import AnomalyDetector
from mplads.risk.rule_engine import RuleEngine


class RiskEngine:
    """
    Central risk engine combining:
    - Anomaly detection
    - Financial risk
    - Compliance/rule risk
    
    Outputs a final risk score (0-100) with explanations.
    """
    
    # Default weights (configurable)
    DEFAULT_WEIGHTS = {
        "anomaly": 0.35,
        "compliance": 0.35,
        "financial": 0.30
    }
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize risk engine.
        
        Args:
            weights: Custom weights for risk components.
                    Must sum to 1.0. If None, uses DEFAULT_WEIGHTS.
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        
        # Validate weights
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        self.anomaly_detector = AnomalyDetector(contamination=0.05)
        self.rule_engine = RuleEngine()
        
    def fit(self, df: pd.DataFrame) -> "RiskEngine":
        """Train the risk engine models."""
        # Fit anomaly detector
        self.anomaly_detector.fit(df)
        return self
    
    def calculate_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate risk scores for all projects."""
        # Get anomaly scores
        result = self.anomaly_detector.predict(df)
        
        # Apply rule engine
        result = self.rule_engine.calculate_compliance_risk(result)
        
        # Calculate financial risk (based on allocation vs mean)
        result["financial_risk"] = self._calculate_financial_risk(result)
        # Additional prototype monitoring signals; legacy overall scores remain unchanged.
        utilization = pd.to_numeric(result.get("utilization_percentage", 0), errors="coerce")
        if not isinstance(utilization, pd.Series):
            utilization = pd.Series(utilization, index=result.index)
        result["utilization_risk"] = ((25 - utilization).clip(lower=0) * 4).clip(0, 100).fillna(0).round(2)
        gap = pd.to_numeric(result.get("progress_gap_percentage", 0), errors="coerce")
        if not isinstance(gap, pd.Series):
            gap = pd.Series(gap, index=result.index)
        result["delay_risk"] = (gap * 2).clip(0, 100).fillna(0).round(2)
        
        # Normalize all risk scores to 0-100
        result["anomaly_risk"] = self._normalize_risk(result["anomaly_score"])
        
        # Ensure compliance_risk exists
        if "compliance_risk" not in result.columns:
            result["compliance_risk"] = 0
        
        # Calculate final weighted risk score
        result["final_risk_score"] = (
            result["anomaly_risk"] * self.weights["anomaly"] +
            result["compliance_risk"] * self.weights["compliance"] +
            result["financial_risk"] * self.weights["financial"]
        ).round(2)
        
        # Classify risk level
        result["risk_level_final"] = result["final_risk_score"].apply(
            self._classify_risk
        )
        
        return result
    
    def _calculate_financial_risk(self, df: pd.DataFrame) -> pd.Series:
        """Calculate financial risk based on allocation patterns."""
        # Use z-score as base
        if "allocation_zscore" in df.columns:
            zscore = pd.to_numeric(df["allocation_zscore"], errors="coerce").fillna(0)
            # Convert z-score to 0-100 risk (|z| * 15, capped at 100)
            risk = (zscore.abs() * 15).clip(0, 100)
        else:
            # Fallback: use allocation vs mean
            mean_alloc = df["allocated_amount"].mean()
            deviation = ((df["allocated_amount"] - mean_alloc).abs() / mean_alloc * 100)
            risk = (deviation / 5).clip(0, 100)  # 5% deviation = 1 risk point
            
        return risk.fillna(0).round(2)
    
    def _normalize_risk(self, scores: pd.Series) -> pd.Series:
        """Normalize scores to 0-100 range."""
        return scores.clip(0, 100)
    
    def _classify_risk(self, score: float) -> str:
        """Classify risk score into level."""
        if score >= 70:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        else:
            return "LOW"
    
    def explain_risk(self, row: pd.Series) -> Dict:
        """
        Generate explanation for why a project was flagged.
        
        Returns a dictionary with risk breakdown and reasons.
        """
        reasons = []
        
        # Anomaly reasons
        if row.get("is_anomaly", False):
            anomaly_detector = AnomalyDetector()
            anomaly_reasons = anomaly_detector.explain_anomaly(row)
            reasons.extend([f"Anomaly: {r}" for r in anomaly_reasons])
        
        # Rule violation reasons
        rule_engine = RuleEngine()
        violations = rule_engine.get_rule_violations(row)
        reasons.extend([f"Rule: {v['rule']} - {v['description']}" for v in violations])
        
        # Financial risk reasons
        if row.get("financial_risk", 0) > 50:
            alloc = row.get("allocated_amount", 0)
            if alloc > 50000000:
                reasons.append("Financial: Very high allocation")
            elif alloc > 25000000:
                reasons.append("Financial: Above average allocation")

        if row.get("rule_critical_utilization", False):
            reasons.append("Prototype Monitoring Rules: Critical utilization below 10%")
        elif row.get("rule_low_utilization", False):
            reasons.append("Prototype Monitoring Rules: Low utilization below 25%")
        if row.get("rule_high_allocation_low_utilization", False):
            reasons.append("High allocation combined with low utilization")
        if row.get("rule_delay_risk", False):
            reasons.append(f"Project progress is {row.get('progress_gap_percentage', 0):.1f} percentage points behind expected progress")
        
        # Build explanation
        explanation = {
            "final_score": row.get("final_risk_score", 0),
            "risk_level": row.get("risk_level_final", "LOW"),
            "components": {
                "anomaly_risk": row.get("anomaly_risk", 0),
                "compliance_risk": row.get("compliance_risk", 0),
                "financial_risk": row.get("financial_risk", 0),
                "utilization_risk": row.get("utilization_risk", 0),
                "delay_risk": row.get("delay_risk", 0)
            },
            "reasons": reasons
        }
        
        return explanation


def calculate_risk_scores(df: pd.DataFrame, 
                          weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """Convenience function to calculate risk scores."""
    engine = RiskEngine(weights=weights)
    engine.fit(df)
    return engine.calculate_risk(df)


if __name__ == "__main__":
    from mplads.data_loader import load_combined_data
    
    df = load_combined_data()
    engine = RiskEngine()
    engine.fit(df)
    result = engine.calculate_risk(df)
    
    high_risk = result[result["risk_level_final"] == "HIGH"]
    print(f"High risk projects: {len(high_risk)}")
    print(f"Medium risk: {len(result[result['risk_level_final'] == 'MEDIUM'])}")
    print(f"Low risk: {len(result[result['risk_level_final'] == 'LOW'])}")
