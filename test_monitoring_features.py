"""Unit tests for prototype monitoring calculations and legacy risk behavior."""
import unittest
import numpy as np
import pandas as pd

from mplads.data_loader import add_prototype_monitoring_fields, prepare_for_anomaly_detection
from mplads.risk.rule_engine import RuleEngine
from mplads.risk.risk_engine import RiskEngine
from mplads.models.anomaly_model import AnomalyDetector
from mplads.models.similarity_model import SimilarityDetector


class MonitoringFeatureTests(unittest.TestCase):
    def test_utilization_and_progress_fields(self):
        raw = pd.DataFrame({"allocated_amount": [1000000, 0], "house": ["Lok Sabha", "Rajya Sabha"], "state": ["A", "B"]})
        result = add_prototype_monitoring_fields(raw, current_date="2026-09-29")
        self.assertTrue((result.utilization_percentage >= 0).all())
        self.assertTrue((result.utilization_percentage <= 100).all())
        self.assertTrue((result.remaining_amount >= 0).all())
        self.assertEqual(result.iloc[1].utilization_percentage, 0)
        self.assertEqual(result.iloc[0].monitoring_data_source, "SIMULATED PROTOTYPE DATA")
        self.assertIn(result.iloc[0].progress_status, {"ON TRACK", "AT RISK", "DELAY RISK"})

    def test_zero_and_null_utilization_safe(self):
        frame = pd.DataFrame({"allocated_amount": [0, np.nan], "utilization_percentage": [np.nan, 0], "progress_gap_percentage": [np.nan, 30]})
        result = RuleEngine().check_all(frame)
        self.assertTrue(result.rule_critical_utilization.iloc[0])
        self.assertTrue(result.rule_delay_risk.iloc[1])

    def test_progress_gap_thresholds_and_monitoring_rules(self):
        frame = pd.DataFrame({"allocated_amount": [60000000, 1000000, 1000000], "utilization_percentage": [8, 18, 40], "progress_gap_percentage": [30, 15, 5]})
        result = RuleEngine().check_all(frame)
        self.assertTrue(result.rule_critical_utilization.iloc[0])
        self.assertTrue(result.rule_high_allocation_low_utilization.iloc[0])
        self.assertTrue(result.rule_delay_risk.iloc[0])
        self.assertTrue(result.rule_low_utilization.iloc[1])
        self.assertFalse(result.rule_delay_risk.iloc[2])

    def test_risk_breakdown_adds_utilization_and_delay(self):
        frame = pd.DataFrame({"allocated_amount": [1000, 2000, 3000, 4000], "allocation_zscore": [0, 0.2, 1, 4], "state_avg_allocation": [2000]*4, "utilization_percentage": [5, 15, 30, 50], "progress_gap_percentage": [0, 12, 30, 2]})
        engine = RiskEngine().fit(frame)
        scored = engine.calculate_risk(frame)
        self.assertIn("utilization_risk", scored)
        self.assertIn("delay_risk", scored)
        self.assertEqual(scored.iloc[0].utilization_risk, 80)
        self.assertEqual(scored.iloc[2].delay_risk, 60)

    def test_anomaly_and_similarity_interfaces_remain(self):
        frame = pd.DataFrame({"project_id": ["L1", "L2", "L3", "L4"], "allocated_amount": [1, 2, 3, 100000], "allocation_zscore": [0, 0, 0, 5], "state_avg_allocation": [2,2,2,2], "state": ["A"]*4, "constituency": ["X"]*4, "mp_name": ["M"]*4, "house": ["Lok Sabha"]*4})
        anomaly = AnomalyDetector(contamination=0.25).fit(frame).predict(frame)
        self.assertEqual(len(anomaly), 4)
        similar, pairs = SimilarityDetector(threshold=0.5).detect_similar(frame)
        self.assertTrue(similar.has_similar.any())
        self.assertTrue(pairs)
        self.assertIn("matching_features", pairs[0])

    def test_anomaly_prep_handles_null_allocation_and_zero_state_average(self):
        frame = pd.DataFrame({"allocated_amount": [None, 0], "state_avg_allocation": [0, None]})
        features, columns = prepare_for_anomaly_detection(frame)
        self.assertTrue(np.isfinite(features["allocation_log"]).all())
        self.assertTrue(np.isfinite(features["allocation_vs_state"]).all())
        self.assertIn("allocated_amount", columns)


if __name__ == "__main__": unittest.main()
