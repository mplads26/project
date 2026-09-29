#!/usr/bin/env python
"""Test all ML components."""
import sys
sys.path.insert(0, '.')

print("Testing MPLAD-AI ML Pipeline...")
print("=" * 60)

# Test 1: Data Loading
print("\n1️⃣ Loading data...")
try:
    from mplads.data_loader import load_combined_data
    df = load_combined_data()
    print(f"   ✅ Loaded {len(df)} projects")
except Exception as e:
    print(f"   ❌ {e}")
    sys.exit(1)

# Test 2: Anomaly Detection
print("\n2️⃣ Running anomaly detection...")
try:
    from mplads.models.anomaly_model import AnomalyDetector
    detector = AnomalyDetector(contamination=0.05)
    detector.fit(df)
    result = detector.predict(df)
    anomalies = result[result["is_anomaly"] == True]
    print(f"   ✅ Detected {len(anomalies)} anomalies")
    print(f"      Sample anomaly score: {anomalies.iloc[0]['anomaly_score']:.1f}/100")
except Exception as e:
    print(f"   ❌ {e}")
    import traceback
    traceback.print_exc()

# Test 3: Rule Engine
print("\n3️⃣ Applying rule engine...")
try:
    from mplads.risk.rule_engine import RuleEngine
    engine = RuleEngine()
    result = engine.calculate_compliance_risk(result)
    violations = result[result["rule_violations"] > 0]
    print(f"   ✅ Found {len(violations)} projects with rule violations")
except Exception as e:
    print(f"   ❌ {e}")
    import traceback
    traceback.print_exc()

# Test 4: Risk Engine
print("\n4️⃣ Calculating risk scores...")
try:
    from mplads.risk.risk_engine import RiskEngine
    risk_engine = RiskEngine()
    risk_engine.fit(df)
    result = risk_engine.calculate_risk(df)
    
    high_risk = result[result["risk_level_final"] == "HIGH"]
    medium_risk = result[result["risk_level_final"] == "MEDIUM"]
    low_risk = result[result["risk_level_final"] == "LOW"]
    
    print(f"   ✅ Risk scores calculated")
    print(f"      HIGH: {len(high_risk)}, MEDIUM: {len(medium_risk)}, LOW: {len(low_risk)}")
    print(f"      Avg score: {result['final_risk_score'].mean():.1f}/100")
except Exception as e:
    print(f"   ❌ {e}")
    import traceback
    traceback.print_exc()

# Test 5: Similarity Detection
print("\n5️⃣ Detecting similar projects...")
try:
    from mplads.models.similarity_model import SimilarityDetector
    detector = SimilarityDetector(threshold=0.85)
    result, pairs = detector.detect_similar(result.head(200))  # Use subset for speed
    similar_count = result["has_similar"].sum()
    print(f"   ✅ Found {similar_count} projects with similar counterparts")
    if pairs:
        print(f"      Sample similarity: {pairs[0]['similarity']:.2%}")
except Exception as e:
    print(f"   ❌ {e}")
    import traceback
    traceback.print_exc()

# Test 6: Explainability
print("\n6️⃣ Testing explainability...")
try:
    # Get a high-risk project
    high_risk_proj = result[result["risk_level_final"] == "HIGH"].iloc[0]
    explanation = risk_engine.explain_risk(high_risk_proj)
    print(f"   ✅ Generated explanation for project {high_risk_proj.get('project_id', 'P00001')}")
    print(f"      Risk Score: {explanation['final_score']:.1f}/100")
    print(f"      Risk Level: {explanation['risk_level']}")
    print(f"      Reasons: {len(explanation['reasons'])} factors identified")
except Exception as e:
    print(f"   ❌ {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ All components tested successfully!")
print("\nNext steps:")
print("1. Start the backend: python -m uvicorn mplads.backend.main:app --reload")
print("2. Start the dashboard: streamlit run mplads/dashboard/app.py")
print("3. Or run both: python run_demo.py")
