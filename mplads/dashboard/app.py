"""Streamlit dashboard for MPLADS risk monitoring and human investigation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import os

API_BASE = os.environ.get("API_BASE", "http://localhost:8000").rstrip("/")
if not API_BASE.startswith("http://") and not API_BASE.startswith("https://"):
    if "." in API_BASE:
        API_BASE = f"https://{API_BASE}"
    elif API_BASE in ("localhost", "127.0.0.1"):
        API_BASE = f"http://{API_BASE}:8000"
    else:
        # On Render free tier, private internal networking is disabled.
        # Blueprint host slug (e.g. 'mplads-api-faca') resolves via the public onrender.com domain.
        API_BASE = f"https://{API_BASE}.onrender.com"
st.set_page_config(page_title="MPLADS AI | Monitoring", page_icon="🛡️", layout="wide")
st.markdown("""<style>
.stApp {background:#f4f7fb; color:#1e293b}
.block-container {padding-top:1.2rem}
.hero {background:#163a5f;color:white;padding:1.1rem 1.4rem;border-radius:10px;margin-bottom:1rem}
[data-testid="stMetric"] {background:white;padding:14px;border-radius:9px;border:1px solid #e6ebf1;box-shadow: 0 1px 3px rgba(0,0,0,0.05)}
[data-testid="stMetricLabel"] {color: #475569 !important}
[data-testid="stMetricValue"] {color: #0f172a !important}
[data-testid="stHeader"] {background-color: rgba(244, 247, 251, 0.9) !important}
</style>""", unsafe_allow_html=True)


class APIError(Exception): pass


def api(path, method="get", **kwargs):
    try:
        response = requests.request(method, f"{API_BASE}{path}", timeout=60, **kwargs)
        response.raise_for_status()
        return response.json() if "application/json" in response.headers.get("content-type", "") else response.content
    except requests.RequestException as exc:
        st.error(f"Backend unavailable: {exc}")
        raise APIError from exc


def currency(value):
    try:
        n = float(value)
    except (TypeError, ValueError): return "—"
    return f"₹{n:,.0f}"


def summary_data(): return api("/dashboard/summary")


def projects(limit=1000, **filters):
    query = {"limit": limit, **{k: v for k, v in filters.items() if v}}
    return api("/projects", params=query)


def show_detail(project_id, key_prefix="detail"):
    detail = api(f"/projects/{project_id}")
    st.markdown(f"### Project Investigation · {detail['project_id']}")
    st.caption("Source data includes real allocation records. Expenditure and lifecycle values below are simulated prototype data.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("State", detail["state"]); c2.metric("MP", detail["mp_name"]); c3.metric("House", detail["house"]); c4.metric("Allocated", currency(detail["allocated_amount"]))
    st.subheader("WHY IS THIS PROJECT FLAGGED?")
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.metric("Risk Score", f"{detail['risk_score']:.1f} / 100", detail["risk_level"])
        components = detail["risk_explanation"]["components"]
        chart_data = pd.DataFrame({"Risk factor": ["Anomaly", "Compliance", "Financial", "Utilization", "Delay"],
                                   "Risk": [components.get("anomaly_risk", 0), components.get("compliance_risk", 0), components.get("financial_risk", 0), components.get("utilization_risk", 0), components.get("delay_risk", 0)]})
        fig = px.bar(chart_data, x="Risk", y="Risk factor", orientation="h", range_x=[0,100], color="Risk", color_continuous_scale=["#2e8b57", "#f0ad35", "#cb3c3c"])
        fig.update_layout(height=240, showlegend=False, coloraxis_showscale=False, margin=dict(l=0,r=0,t=5,b=0))
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}-risk-chart-{project_id}")
    with col2:
        st.markdown("**Top applicable reasons**")
        reasons = detail["risk_explanation"].get("reasons", [])
        if reasons:
            for i, reason in enumerate(reasons[:5], 1): st.write(f"{i}. {reason}")
        else: st.info("No specific risk reasons apply. This project is not flagged.")
        st.info("Risk indicators support human review. An anomaly is not a finding of fraud.")

    st.subheader("Expenditure & Utilization · Prototype Monitoring Rules")
    finance = st.columns(4)
    for col, label, key in zip(finance, ["Allocated", "Released", "Expenditure", "Remaining"], ["allocated_amount", "released_amount", "expenditure_amount", "remaining_amount"]): col.metric(label, currency(detail[key]))
    utilization = max(0, min(float(detail["utilization_percentage"]), 100))
    st.progress(int(utilization), text=f"Utilization: {utilization:.1f}%")
    if utilization < 10: st.error("CRITICAL UTILIZATION · Prototype threshold below 10%")
    elif utilization < 25: st.warning("LOW UTILIZATION · Prototype threshold below 25%")

    st.subheader("Project Progress · Prototype Monitoring Logic")
    expected, actual, gap = st.columns(3)
    expected.metric("Expected Progress", f"{detail['expected_progress_percentage']:.1f}%")
    actual.metric("Actual Progress", f"{detail['project_progress_percentage']:.1f}%")
    gap.metric("Progress Gap", f"{detail['progress_gap_percentage']:.1f} pp", detail["progress_status"])
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Expected", x=[detail["expected_progress_percentage"]], y=["Progress"], orientation="h", marker_color="#8aa6c1"))
    fig.add_trace(go.Bar(name="Actual", x=[detail["project_progress_percentage"]], y=["Progress"], orientation="h", marker_color="#1e6594"))
    fig.update_layout(barmode="overlay", height=150, xaxis_range=[0,100], margin=dict(l=5,r=5,t=10,b=5))
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}-progress-chart-{project_id}")
    st.caption(f"Status: **{detail['progress_status']}** — AT RISK when gap >10 pp; DELAY RISK when gap >25 pp. Prototype logic only.")

    st.subheader("Project Health")
    health = api(f"/projects/{project_id}/health")
    cols = st.columns(4)
    for col, (label, key) in zip(cols, [("Financial", "financial_health"), ("Compliance", "compliance_health"), ("Utilization", "utilization_health"), ("Progress", "progress_health")]):
        col.metric(f"{label} Health", f"{health[key]:.0f}/100"); col.progress(int(max(0,min(100,health[key]))))
    st.caption(f"Overall Risk: {health['overall_risk']:.1f}/100 · Additional health visualization; does not replace the risk score.")

    st.subheader("Potentially Similar Projects")
    if detail.get("similar_projects"):
        st.warning("Potentially Similar Projects — Requires Human Verification")
        for similar in detail["similar_projects"]:
            st.markdown(f"**{detail['project_id']} ↔ {similar['project_id']}** · {similar['similarity']:.0%} similarity · {similar['state']} · {similar.get('mp_name','N/A')} · {currency(similar.get('allocated_amount',0))}")
            st.caption("Matching metadata: " + (", ".join(similar.get("matching_features", [])) or "text features"))
    else: st.info("No project exceeded the configured similarity threshold.")

    st.subheader("Project Lifecycle Timeline · Simulated Dates")
    dates = [pd.to_datetime(detail.get("project_start_date")), pd.to_datetime(detail.get("expected_completion_date"))]
    st.markdown(f"Approved → Funds released → Work started ({dates[0].date()}) → Progress updated ({detail['project_progress_percentage']:.0f}%) → Risk monitoring → Human review ({detail['review_status']})")
    st.caption("Lifecycle dates are simulated demonstration values; no government dates were present in the source dataset.")

    st.subheader("Human Review")
    statuses = ["PENDING REVIEW", "UNDER INVESTIGATION", "VERIFIED", "FALSE POSITIVE", "RESOLVED"]
    try: initial_idx = statuses.index(detail.get("review_status", "PENDING REVIEW"))
    except ValueError: initial_idx = 0
    status = st.selectbox("Review Status", statuses, index=initial_idx, key=f"{key_prefix}-status-{project_id}")
    comment = st.text_area("Reviewer Comment", value=detail.get("review_comment", ""), key=f"{key_prefix}-comment-{project_id}")
    if st.button("Save Review", key=f"{key_prefix}-save-{project_id}"):
        api(f"/projects/{project_id}/review", method="put", json={"status": status, "comment": comment})
        st.success("Review updated for this session.")
    pdf = api(f"/projects/{project_id}/report")
    st.download_button("Generate Investigation Report (PDF)", pdf, file_name=f"mplads-{project_id}-report.pdf", mime="application/pdf", key=f"{key_prefix}-report-{project_id}")


def main():
    st.markdown("<div class='hero'><h1>🛡️ MPLADS AI — Intelligent Risk & Monitoring</h1><div>Smart India Hackathon 2026 · Problem Statement 26102 · Human-led investigation support</div></div>", unsafe_allow_html=True)
    try: summary = summary_data()
    except APIError:
        st.warning("Start the FastAPI service to load the monitoring dashboard.")
        st.code("python -m uvicorn mplads.backend.main:app --port 8000")
        return
    st.caption("Prototype monitoring rules · Financial and progress indicators are simulated demo fields, not official government records or thresholds.")
    metrics = st.columns(6)
    for col, label, value in zip(metrics, ["Projects", "High Risk", "Medium Risk", "Low Risk", "Potential Anomalies", "Potential Similar"], [summary["total_projects"], summary["high_risk"], summary["medium_risk"], summary["low_risk"], summary["potential_anomalies"], summary["potential_duplicates"]]): col.metric(label, f"{value:,}")
    tabs = st.tabs(["Overview", "Risk Alerts", "Projects", "Project Investigation", "State Analysis", "Project Health", "Reports"])
    try:
        all_projects = projects(limit=1000)
        project_ids = [p["project_id"] for p in all_projects]
    except APIError: return

    with tabs[0]:
        counts = summary["risk_distribution"]
        fig = px.pie(names=list(counts), values=list(counts.values()), hole=.48, color=list(counts), color_discrete_map={"HIGH":"#c93c3c","MEDIUM":"#f0ad35","LOW":"#2e8b57"}, title="Risk Distribution")
        st.plotly_chart(fig, use_container_width=True, key="overview-risk-pie")
        states = api("/risk/distribution")
        state_data = [{"State":s,"HIGH":v["HIGH"],"MEDIUM":v["MEDIUM"],"LOW":v["LOW"],"Total":sum(v.values())} for s,v in states.items()]
        state_df = pd.DataFrame(state_data).sort_values("Total", ascending=False)
        fig=px.bar(state_df.head(20),x="State",y=["HIGH","MEDIUM","LOW"],barmode="stack",color_discrete_map={"HIGH":"#c93c3c","MEDIUM":"#f0ad35","LOW":"#2e8b57"},title="State-wise Risk Distribution")
        st.plotly_chart(fig, use_container_width=True, key="overview-state-bar")

    with tabs[1]:
        states = api("/states")["states"]
        a,b,c=st.columns(3)
        risk_filter=a.selectbox("Risk level",["All","HIGH","MEDIUM","LOW"],key="alert-risk")
        type_filter=b.selectbox("Alert type",["All","HIGH RISK","MEDIUM RISK","LOW RISK","ANOMALY","LOW UTILIZATION","DELAY RISK","SIMILAR PROJECT"],key="alert-type")
        state_filter=c.selectbox("State",["All"]+states,key="alert-state")
        query={"limit":200}
        if risk_filter!="All": query["risk_level"]=risk_filter
        if type_filter!="All": query["alert_type"]=type_filter
        if state_filter!="All": query["state"]=state_filter
        alerts=api("/alerts",params=query)
        if alerts:
            alertdf=pd.DataFrame(alerts).sort_values("risk_score",ascending=False)
            st.dataframe(alertdf,hide_index=True,use_container_width=True)
            choices=alertdf["project_id"].tolist()
            selected=st.selectbox("View Project",choices,key="alert-project")
            if st.button("Open selected alert",key="alert-open"): st.session_state["selected_project"]=selected
            if st.session_state.get("selected_project") in choices: show_detail(st.session_state["selected_project"], key_prefix="alert")
        else: st.success("No alerts match these filters.")

    with tabs[2]:
        a,b,c=st.columns(3)
        risk=a.selectbox("Risk",["All","HIGH","MEDIUM","LOW"],key="project-risk")
        state=b.selectbox("State",["All"]+api("/states")["states"],key="project-state")
        limit=c.slider("Rows",20,774,100,key="project-limit")
        records=projects(limit=limit,**({"risk_level":risk} if risk!="All" else {}),**({"state":state} if state!="All" else {}))
        st.dataframe(pd.DataFrame(records),hide_index=True,use_container_width=True)
        selected=st.selectbox("Select project",[p["project_id"] for p in records],key="project-detail-select")
        if selected: st.session_state["selected_project"]=selected

    with tabs[3]:
        default=st.session_state.get("selected_project",project_ids[0] if project_ids else "")
        selected=st.selectbox("Project ID",project_ids,index=project_ids.index(default) if default in project_ids else 0,key="investigation-select")
        if selected: show_detail(selected, key_prefix="investigation")

    with tabs[4]:
        states=api("/states")["states"]
        selected_state=st.selectbox("Select a state",states,key="analysis-state")
        data=api(f"/states/{requests.utils.quote(selected_state, safe='')}/summary")
        c=st.columns(6)
        for col,label,key in zip(c,["Projects","High","Medium","Low","Average Risk","Allocation"],["total_projects","high_risk","medium_risk","low_risk","average_risk_score","total_allocation"]): col.metric(label,currency(data[key]) if key=="total_allocation" else f"{data[key]:.1f}" if key=="average_risk_score" else data[key])
        subset=[p for p in all_projects if p["state"]==selected_state]
        st.dataframe(pd.DataFrame(subset),hide_index=True,use_container_width=True)

    with tabs[5]:
        candidates=[p for p in all_projects if p.get("risk_level")=="HIGH"] or all_projects
        selected=st.selectbox("Project for health view",[p["project_id"] for p in candidates],key="health-select")
        if selected: show_detail(selected, key_prefix="health")

    with tabs[6]:
        selected=st.selectbox("Project for report",project_ids,key="report-select")
        if selected:
            detail=api(f"/projects/{selected}")
            st.write(f"Report will include risk explanation, financial and progress monitoring, similarity, and human review details for **{selected}**.")
            payload=api(f"/projects/{selected}/report")
            st.download_button("Download Investigation Report PDF",payload,file_name=f"mplads-{selected}-report.pdf",mime="application/pdf", key=f"report-tab-dl-{selected}")
            st.caption("Report contains simulated prototype monitoring values where source expenditure and progress records are unavailable.")

    st.divider()
    st.caption("MPLADS AI prototype · Risk indicators require human verification. No anomaly is a finding of fraud.")


if __name__ == "__main__": main()
