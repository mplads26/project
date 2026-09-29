"""
MPLADS Risk Analysis API - FastAPI backend for the prototype.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO

from mplads.data_loader import load_combined_data
from mplads.models.anomaly_model import AnomalyDetector
from mplads.models.similarity_model import SimilarityDetector
from mplads.risk.rule_engine import RuleEngine
from mplads.risk.risk_engine import RiskEngine

# Global state
_app_state = {
    "data": None,
    "risk_results": None,
    "similarity_detector": None,
    "last_updated": None,
    "reviews": {}
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize data on startup."""
    print("Loading MPLADS data...")
    load_data()
    print(f"Loaded {len(_app_state['data'])} projects")
    yield
    print("Shutting down...")


app = FastAPI(
    title="MPLAD-AI API",
    description="AI-Powered Risk Monitoring for MPLADS Scheme",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class RiskExplanation(BaseModel):
    final_score: float
    risk_level: str
    components: Dict[str, float]
    reasons: List[str]


class SimilarProject(BaseModel):
    project_id: str
    similarity: float
    mp_name: str
    state: str
    allocated_amount: Optional[float] = None
    house: Optional[str] = None
    matching_features: List[str] = []


class ProjectDetail(BaseModel):
    project_id: str
    state: str
    constituency: Optional[str] = None
    mp_name: str
    house: str
    allocated_amount: float
    anomaly_score: Optional[float] = None
    anomaly_flag: Optional[bool] = None
    risk_score: float
    risk_level: str
    max_similarity: Optional[float] = None
    review_status: Optional[str] = "PENDING REVIEW"
    risk_explanation: RiskExplanation
    similar_projects: List[SimilarProject] = []
    released_amount: float = 0
    expenditure_amount: float = 0
    remaining_amount: float = 0
    utilization_percentage: float = 0
    expected_progress_percentage: float = 0
    project_progress_percentage: float = 0
    progress_gap_percentage: float = 0
    progress_status: str = "ON TRACK"
    review_comment: str = ""
    monitoring_data_source: str = "SIMULATED PROTOTYPE DATA"
    project_start_date: Optional[str] = None
    expected_completion_date: Optional[str] = None


class DashboardSummary(BaseModel):
    total_projects: int
    high_risk: int
    medium_risk: int
    low_risk: int
    potential_anomalies: int
    potential_duplicates: int
    pending_review: int
    risk_distribution: Dict[str, int]


class AlertItem(BaseModel):
    project_id: str
    state: str
    mp_name: str
    risk_score: float
    risk_level: str
    alert_type: str
    reason: str


class ReviewUpdate(BaseModel):
    status: str
    comment: str = ""


def load_data():
    """Load and process all data."""
    print("Loading combined data...")
    df = load_combined_data()
    
    print("Calculating risk scores...")
    risk_engine = RiskEngine()
    risk_engine.fit(df)
    risk_results = risk_engine.calculate_risk(df)
    
    print("Applying prototype monitoring rules...")
    rule_engine = RuleEngine()
    risk_results = rule_engine.check_all(risk_results)
    
    print("Detecting similar projects...")
    similarity_detector = SimilarityDetector(threshold=0.85)
    risk_results, _ = similarity_detector.detect_similar(risk_results)
    
    # Store in state
    _app_state["data"] = df
    _app_state["risk_results"] = risk_results
    _app_state["similarity_detector"] = similarity_detector
    _app_state["last_updated"] = datetime.now()
    
    print("Data initialization complete.")


# API Endpoints

@app.get("/")
async def root():
    return {
        "name": "MPLAD-AI API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary():
    """Get dashboard summary statistics."""
    df = _app_state["risk_results"]
    
    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    return DashboardSummary(
        total_projects=len(df),
        high_risk=int(len(df[df["risk_level_final"] == "HIGH"])),
        medium_risk=int(len(df[df["risk_level_final"] == "MEDIUM"])),
        low_risk=int(len(df[df["risk_level_final"] == "LOW"])),
        potential_anomalies=int(len(df[df["is_anomaly"] == True])),
        potential_duplicates=int(len(df[df["has_similar"] == True])),
        pending_review=len(df),
        risk_distribution={
            "HIGH": int(len(df[df["risk_level_final"] == "HIGH"])),
            "MEDIUM": int(len(df[df["risk_level_final"] == "MEDIUM"])),
            "LOW": int(len(df[df["risk_level_final"] == "LOW"]))
        }
    )


@app.get("/projects", response_model=List[Dict[str, Any]])
async def get_projects(
    risk_level: Optional[str] = Query(None, regex="^(HIGH|MEDIUM|LOW)$"),
    state: Optional[str] = None,
    house: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    """Get list of projects with optional filtering."""
    df = _app_state["risk_results"]
    
    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    # Apply filters
    if risk_level:
        df = df[df["risk_level_final"] == risk_level]
    if state:
        df = df[df["state"] == state]
    if house:
        df = df[df["house"] == house]
    
    # Pagination
    df = df.iloc[offset:offset + limit]
    
    # Convert to list of dicts
    result = []
    for _, row in df.iterrows():
        result.append({
            "project_id": row.get("project_id", f"P{row.name}"),
            "state": row.get("state", "N/A"),
            "mp_name": row.get("mp_name", "N/A"),
            "house": row.get("house", "N/A"),
            "allocated_amount": float(row.get("allocated_amount", 0)),
            "risk_score": float(row.get("final_risk_score", 0)),
            "risk_level": row.get("risk_level_final", "LOW"),
            "is_anomaly": bool(row.get("is_anomaly", False)),
            "has_similar": bool(row.get("has_similar", False)),
            "utilization_percentage": float(row.get("utilization_percentage", 0)),
            "progress_gap_percentage": float(row.get("progress_gap_percentage", 0)),
            "progress_status": row.get("progress_status", "ON TRACK")
        })
    
    return result


@app.get("/alerts", response_model=List[AlertItem])
async def get_alerts(
    risk_level: Optional[str] = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"),
    limit: int = Query(200, le=200),
    alert_type: Optional[str] = None,
    state: Optional[str] = None
):
    """Get alerts for high-priority projects."""
    df = _app_state["risk_results"]
    
    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    alerts = []
    candidates = []
    descriptions = {"ANOMALY": "Potential statistical anomaly; review recommended",
        "LOW UTILIZATION": "Prototype monitoring threshold: utilization below 25%",
        "DELAY RISK": "Prototype progress gap exceeds 25 percentage points",
        "SIMILAR PROJECT": "Potentially similar projects require human verification"}
    for _, row in df.iterrows():
        kinds = []
        if row.get("risk_level_final") in ("HIGH", "MEDIUM"): kinds.append(f"{row['risk_level_final']} RISK")
        if row.get("is_anomaly", False): kinds.append("ANOMALY")
        if row.get("risk_level_final") == "LOW": kinds.append("LOW RISK")
        if float(row.get("utilization_percentage", 100)) < 25: kinds.append("LOW UTILIZATION")
        if row.get("progress_status") == "DELAY RISK": kinds.append("DELAY RISK")
        if row.get("has_similar", False): kinds.append("SIMILAR PROJECT")
        if risk_level and not any(kind == f"{risk_level} RISK" for kind in kinds): continue
        for kind in kinds:
            if alert_type and kind != alert_type: continue
            if state and str(row.get("state")) != state: continue
            reason = descriptions.get(kind, f"Composite risk score is in the {kind.lower()} band")
            if kind == "LOW UTILIZATION": reason = f"Prototype utilization is {float(row.get('utilization_percentage', 0)):.1f}%"
            if kind == "DELAY RISK": reason = f"Prototype progress gap is {float(row.get('progress_gap_percentage', 0)):.1f} points"
            candidates.append((row, kind, reason))
    candidates.sort(key=lambda item: float(item[0].get("final_risk_score", 0)), reverse=True)
    for row, kind, reason in candidates[:limit]:
        alerts.append(AlertItem(
            project_id=row.get("project_id", f"P{row.name}"),
            state=row.get("state", "N/A"),
            mp_name=row.get("mp_name", "N/A"),
            risk_score=float(row.get("final_risk_score", 0)),
            risk_level=row.get("risk_level_final", "LOW"),
            alert_type=kind,
            reason=reason
        ))
    
    return alerts


@app.get("/states")
async def get_states():
    """Get list of unique states."""
    df = _app_state["risk_results"]
    
    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    states = sorted(df["state"].unique().tolist())
    return {"states": states}


@app.get("/risk/distribution")
async def get_risk_distribution():
    """Get risk distribution by state."""
    df = _app_state["risk_results"]
    
    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    distribution = df.groupby(["state", "risk_level_final"]).size().unstack(fill_value=0)
    
    result = {}
    for state in distribution.index:
        result[state] = {
            "HIGH": int(distribution.loc[state].get("HIGH", 0)),
            "MEDIUM": int(distribution.loc[state].get("MEDIUM", 0)),
            "LOW": int(distribution.loc[state].get("LOW", 0))
        }
    
    return result


@app.get("/projects/{project_id}/health")
async def get_project_health(project_id: str):
    row = _find_project(project_id)
    return {"overall_risk": float(row.get("final_risk_score", 0)),
            "financial_health": round(100 - float(row.get("financial_risk", 0)), 2),
            "compliance_health": round(100 - float(row.get("compliance_risk", 0)), 2),
            "utilization_health": round(100 - float(row.get("utilization_risk", 0)), 2),
            "progress_health": round(100 - float(row.get("delay_risk", 0)), 2)}


def _find_project(project_id: str) -> pd.Series:
    df = _app_state["risk_results"]
    if df is None: raise HTTPException(status_code=503, detail="Data not loaded")
    match = df[df["project_id"].astype(str) == str(project_id)]
    if match.empty: raise HTTPException(status_code=404, detail="Project not found")
    return match.iloc[0]


@app.get("/states/{state}/summary")
async def get_state_summary(state: str):
    df = _app_state["risk_results"]
    if df is None: raise HTTPException(status_code=503, detail="Data not loaded")
    subset = df[df["state"].astype(str).str.casefold() == state.casefold()]
    if subset.empty: raise HTTPException(status_code=404, detail="State not found")
    return {"state": state, "total_projects": len(subset),
            "high_risk": int((subset["risk_level_final"] == "HIGH").sum()),
            "medium_risk": int((subset["risk_level_final"] == "MEDIUM").sum()),
            "low_risk": int((subset["risk_level_final"] == "LOW").sum()),
            "average_risk_score": round(float(subset["final_risk_score"].mean()), 2),
            "total_allocation": float(subset["allocated_amount"].sum())}


@app.put("/projects/{project_id}/review")
async def update_review(project_id: str, review: ReviewUpdate):
    _find_project(project_id)
    _app_state["reviews"][project_id] = {"status": review.status, "comment": review.comment}
    return {"project_id": project_id, **_app_state["reviews"][project_id]}


@app.get("/projects/{project_id}/report")
async def project_report(project_id: str):
    from fastapi.responses import StreamingResponse
    row = _find_project(project_id)
    review = _app_state["reviews"].get(project_id, {"status": "PENDING REVIEW", "comment": ""})
    reasons = RiskEngine().explain_risk(row).get("reasons", [])
    lines = [f"Project ID: {project_id}", f"State: {row.get('state', 'N/A')}",
        f"MP Name: {row.get('mp_name', 'N/A')}", f"House: {row.get('house', 'N/A')}",
        f"Risk Score: {row.get('final_risk_score', 0):.1f}/100", f"Risk Level: {row.get('risk_level_final', 'LOW')}",
        "", "RISK BREAKDOWN", f"Anomaly {row.get('anomaly_risk', 0):.1f} | Compliance {row.get('compliance_risk', 0):.1f} | Financial {row.get('financial_risk', 0):.1f}",
        f"Utilization {row.get('utilization_risk', 0):.1f} | Delay {row.get('delay_risk', 0):.1f}", "", "WHY FLAGGED", *reasons,
        "", "PROJECT FINANCIAL INFORMATION - SIMULATED PROTOTYPE DATA",
        f"Allocated {row.get('allocated_amount', 0):,.0f} | Released {row.get('released_amount', 0):,.0f}",
        f"Expenditure {row.get('expenditure_amount', 0):,.0f} | Remaining {row.get('remaining_amount', 0):,.0f}",
        f"Utilization {row.get('utilization_percentage', 0):.1f}%", "", "PROJECT PROGRESS — SIMULATED PROTOTYPE DATA",
        f"Expected {row.get('expected_progress_percentage', 0):.1f}% | Actual {row.get('project_progress_percentage', 0):.1f}%",
        f"Gap {row.get('progress_gap_percentage', 0):.1f} points | Status {row.get('progress_status', 'N/A')}",
        "", "SIMILARITY INFORMATION", "Potentially similar project — requires human verification." if row.get("has_similar", False) else "No project exceeded the configured similarity threshold.",
        "", f"Human Review Status: {review['status']}", f"Reviewer Comment: {review.get('comment', '')}",
        f"Report generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "Prototype thresholds and simulated values are not official Government of India rules or data."]
    buffer = BytesIO(_make_pdf(lines))
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="mplads-{project_id}-report.pdf"'})


def _make_pdf(lines: List[str]) -> bytes:
    """Build a simple multi-page PDF with built-in Python only."""
    import textwrap
    safe_lines = []
    for line in lines:
        normalized = str(line).encode("ascii", "replace").decode("ascii")
        safe_lines.extend(textwrap.wrap(normalized, width=92) or [""])
    chunks = [safe_lines[i:i + 48] for i in range(0, len(safe_lines), 48)] or [[]]
    objects = []
    def add(obj: bytes) -> int:
        objects.append(obj); return len(objects)
    catalog_id = add(b"")
    pages_id = add(b"")
    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    for page_lines in chunks:
        commands = ["BT", "/F1 14 Tf", "50 790 Td", "(MPLADS AI RISK MONITORING REPORT) Tj", "/F1 9 Tf", "0 -28 Td"]
        for line in page_lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.extend([f"({escaped}) Tj", "0 -14 Td"])
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii", "replace")
        content_id = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_id = add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode())
        page_ids.append(page_id)
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode()
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    output = bytearray(b"%PDF-1.4\n% MPLADS AI Report\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f"{index} 0 obj\n".encode()); output.extend(obj); output.extend(b"\nendobj\n")
    xref = len(output); output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]: output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


@app.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project_detail(project_id: str):
    """Backward-compatible detailed view for one project."""
    df = _app_state["risk_results"]
    if df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    matches = df[df["project_id"].astype(str) == str(project_id)]
    if matches.empty:
        raise HTTPException(status_code=404, detail="Project not found")
    idx, project = matches.index[0], matches.iloc[0]
    detector = _app_state.get("similarity_detector") or SimilarityDetector(threshold=0.85)
    similar_projects = detector.get_similar_for_project(df, idx)
    explanation = RiskEngine().explain_risk(project)
    review = _app_state["reviews"].get(project_id, {"status": "PENDING REVIEW", "comment": ""})
    return ProjectDetail(
        project_id=str(project.get("project_id")), state=str(project.get("state", "N/A")),
        constituency=project.get("constituency"), mp_name=str(project.get("mp_name", "N/A")),
        house=str(project.get("house", "N/A")), allocated_amount=float(project.get("allocated_amount", 0)),
        anomaly_score=float(project.get("anomaly_score", 0)), anomaly_flag=bool(project.get("is_anomaly", False)),
        risk_score=float(project.get("final_risk_score", 0)), risk_level=str(project.get("risk_level_final", "LOW")),
        max_similarity=float(project.get("max_similarity", 0)), review_status=review["status"],
        risk_explanation=RiskExplanation(**explanation),
        similar_projects=[SimilarProject(**p) for p in similar_projects[:5]],
        released_amount=float(project.get("released_amount", 0)), expenditure_amount=float(project.get("expenditure_amount", 0)),
        remaining_amount=float(project.get("remaining_amount", 0)), utilization_percentage=float(project.get("utilization_percentage", 0)),
        expected_progress_percentage=float(project.get("expected_progress_percentage", 0)),
        project_progress_percentage=float(project.get("project_progress_percentage", 0)),
        progress_gap_percentage=float(project.get("progress_gap_percentage", 0)), progress_status=str(project.get("progress_status", "ON TRACK")),
        review_comment=review.get("comment", ""), monitoring_data_source=str(project.get("monitoring_data_source", "SIMULATED PROTOTYPE DATA")),
        project_start_date=str(project.get("project_start_date", ""))[:10],
        expected_completion_date=str(project.get("expected_completion_date", ""))[:10])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

