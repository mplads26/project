"""Rule-based compliance checking for MPLADS projects."""
import pandas as pd
from typing import List, Dict, Tuple


class RuleEngine:
    """
    Rule-based checks for MPLADS compliance.
    
    These are system-defined risk heuristics, not official government rules
    unless explicitly noted.
    """
    
    def __init__(self):
        self.rules = [
            {
                "id": "high_allocation",
                "name": "High Allocation",
                "description": "Allocation exceeds threshold",
                "threshold": 50000000,  # 5 Crore
                "severity": "medium"
            },
            {
                "id": "very_high_allocation",
                "name": "Very High Allocation", 
                "description": "Allocation significantly exceeds normal range",
                "threshold": 100000000,  # 10 Crore
                "severity": "high"
            },
            {
                "id": "low_allocation",
                "name": "Low Allocation",
                "description": "Allocation below typical range",
                "threshold": 500000,  # 5 Lakh
                "severity": "low"
            },
            {
                "id": "extreme_zscore",
                "name": "Extreme Z-Score",
                "description": "Allocation is statistical outlier",
                "threshold": 3.0,
                "severity": "high"
            }
        ]
    
    def check_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all rules to the dataset."""
        result = df.copy()
        
        # Ensure numeric
        result["allocated_amount"] = pd.to_numeric(
            result["allocated_amount"], errors="coerce"
        ).fillna(0)
        
        # Rule 1: High allocation
        result["rule_high_allocation"] = (
            result["allocated_amount"] > 50000000
        )
        
        # Rule 2: Very high allocation
        result["rule_very_high_allocation"] = (
            result["allocated_amount"] > 100000000
        )
        
        # Rule 3: Low allocation
        result["rule_low_allocation"] = (
            result["allocated_amount"] < 500000
        )
        
        # Rule 4: Extreme z-score
        if "allocation_zscore" in result.columns:
            result["allocation_zscore"] = pd.to_numeric(
                result["allocation_zscore"], errors="coerce"
            ).fillna(0)
            result["rule_extreme_zscore"] = (
                result["allocation_zscore"].abs() > 3.0
            )
        else:
            result["rule_extreme_zscore"] = False
        
        # Rule 5: Risk level already in data
        if "risk_level" in result.columns:
            result["rule_existing_high_risk"] = (
                result["risk_level"] == "High"
            )
        else:
            result["rule_existing_high_risk"] = False

        # Prototype monitoring rules. These are demonstration indicators, not
        # official Government of India thresholds.
        utilization = pd.to_numeric(result.get("utilization_percentage", pd.Series(index=result.index, dtype=float)), errors="coerce").fillna(0)
        allocation = pd.to_numeric(result["allocated_amount"], errors="coerce").fillna(0)
        result["rule_critical_utilization"] = utilization.lt(10).fillna(False)
        result["rule_low_utilization"] = utilization.lt(25).fillna(False) & ~result["rule_critical_utilization"]
        result["rule_high_allocation_low_utilization"] = (allocation >= 50000000) & utilization.lt(25).fillna(False)
        gap = pd.to_numeric(result.get("progress_gap_percentage", pd.Series(index=result.index, dtype=float)), errors="coerce").fillna(0)
        result["rule_delay_risk"] = gap.gt(25).fillna(False)
        
        # Calculate compliance score (inverse of rule violations)
        monitoring_rule_cols = {"rule_critical_utilization", "rule_low_utilization", "rule_high_allocation_low_utilization", "rule_delay_risk"}
        rule_cols = [col for col in result.columns if col.startswith("rule_") and col not in monitoring_rule_cols and col != "rule_violations"]
        result["rule_violations"] = result[rule_cols].sum(axis=1)
        result["compliance_score"] = 100 - (result["rule_violations"] * 20).clip(0, 100)
        
        return result
    
    def get_rule_violations(self, row: pd.Series) -> List[Dict]:
        """Get list of rule violations for a specific project."""
        violations = []
        
        if row.get("rule_high_allocation", False):
            violations.append({
                "rule": "High Allocation",
                "description": "Allocation exceeds ₹5 Crore",
                "severity": "medium"
            })
        
        if row.get("rule_very_high_allocation", False):
            violations.append({
                "rule": "Very High Allocation",
                "description": "Allocation exceeds ₹10 Crore", 
                "severity": "high"
            })
        
        if row.get("rule_low_allocation", False):
            violations.append({
                "rule": "Low Allocation",
                "description": "Allocation below ₹5 Lakh",
                "severity": "low"
            })
        
        if row.get("rule_extreme_zscore", False):
            zscore = row.get("allocation_zscore", 0)
            violations.append({
                "rule": "Extreme Z-Score",
                "description": f"Z-score: {zscore:.2f} (|z| > 3)",
                "severity": "high"
            })
        
        if row.get("rule_existing_high_risk", False):
            violations.append({
                "rule": "Existing High Risk",
                "description": "Previously flagged as high risk",
                "severity": "medium"
            })

        if row.get("rule_critical_utilization", False):
            violations.append({"rule": "Critical Utilization", "description": "Prototype monitoring rule: utilization below 10%", "severity": "high"})
        elif row.get("rule_low_utilization", False):
            violations.append({"rule": "Low Utilization", "description": "Prototype monitoring rule: utilization below 25%", "severity": "medium"})
        if row.get("rule_high_allocation_low_utilization", False):
            violations.append({"rule": "High Allocation with Low Utilization", "description": "High allocation combined with utilization below 25%", "severity": "high"})
        if row.get("rule_delay_risk", False):
            violations.append({"rule": "Delay Risk", "description": "Prototype progress gap exceeds 25 percentage points", "severity": "high"})
        
        return violations
    
    def calculate_compliance_risk(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate compliance risk score (0-100)."""
        result = self.check_all(df)
        
        # Inverse of compliance score - higher = more risk
        result["compliance_risk"] = 100 - result["compliance_score"]
        
        return result


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Convenience function to apply all rules."""
    engine = RuleEngine()
    return engine.calculate_compliance_risk(df)


if __name__ == "__main__":
    from mplads.data_loader import load_combined_data
    
    df = load_combined_data()
    result = apply_rules(df)
    
    violations = result[result["rule_violations"] > 0]
    print(f"Found {len(violations)} projects with rule violations")
