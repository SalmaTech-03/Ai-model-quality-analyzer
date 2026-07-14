"""
Streamlit demo UI for the drift analysis API.

Calls your real, running FastAPI service (POST /api/analyze) - this is not a
separate reimplementation of the drift logic, just a clean front end for
taking a screenshot/demo of the real pipeline.

Deliberately avoids the bug visible in your ModelGuard Pro screenshot: this
app only ever renders the response from the CURRENT request. Nothing persists
across runs (no leftover "BIAS DETECTED" from a previous upload sitting next
to a fresh "no drift" result) - every screenshot you take here reflects
exactly the two files you just uploaded, nothing else.

Run with:
    streamlit run drift_streamlit_app.py

Requires your FastAPI server already running (uvicorn app.main:app --reload)
and a valid API_KEY set in your .env.
"""
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Drift Analyzer Demo", layout="wide")

st.sidebar.title("⚙️ Connection")
api_base = st.sidebar.text_input("API base URL", value="http://localhost:8000")
api_key = st.sidebar.text_input("API key (x-api-key)", type="password")

st.title("🔍 Model Drift Analyzer")
st.caption("Live demo front end for the DriftAnalyzer / evidently pipeline.")

col1, col2 = st.columns(2)
with col1:
    ref_file = st.file_uploader("Reference dataset (CSV)", type="csv", key="ref")
with col2:
    curr_file = st.file_uploader("Current dataset (CSV)", type="csv", key="curr")

if ref_file is not None and curr_file is not None:
    if ref_file.name == curr_file.name:
        st.warning(
            f"⚠️ Both files are named '{ref_file.name}'. Make sure you actually "
            "selected two DIFFERENT datasets (reference vs. current) - "
            "uploading the same file as both will trivially show zero drift."
        )

    run = st.button("▶ Run Analysis", type="primary")

    if run:
        if not api_key:
            st.error("Enter your API key in the sidebar first.")
            st.stop()

        with st.spinner("Running drift analysis..."):
            try:
                resp = requests.post(
                    f"{api_base}/api/analyze",
                    headers={"x-api-key": api_key},
                    files={
                        "reference_file": (ref_file.name, ref_file.getvalue(), "text/csv"),
                        "current_file": (curr_file.name, curr_file.getvalue(), "text/csv"),
                    },
                    timeout=120,
                )
            except requests.exceptions.ConnectionError:
                st.error(
                    f"Could not reach {api_base}. Is your FastAPI server running? "
                    "(`uvicorn app.main:app --reload`)"
                )
                st.stop()

        if resp.status_code != 200:
            st.error(f"API returned {resp.status_code}: {resp.text}")
            st.stop()

        data = resp.json()["data"]

        automation = data.get("automation", {})
        action = automation.get("action", "UNKNOWN")
        color = automation.get("color", "#888")

        st.markdown(
            f"""
            <div style="padding: 1.2rem; border-radius: 8px; background-color: {color}22;
                        border: 2px solid {color}; margin-bottom: 1rem;">
                <h2 style="color: {color}; margin: 0;">{action}</h2>
                <p style="margin: 0.3rem 0 0 0;">{automation.get('details', '')}</p>
                <p style="margin: 0.3rem 0 0 0; font-size: 0.85rem; opacity: 0.8;">
                    Rule: {automation.get('rule', 'N/A')} · Pipeline: {automation.get('pipeline', 'N/A')}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        meta = data.get("meta", {})
        health = data.get("model_health", {})
        financials = data.get("financials", {})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Model Version", meta.get("version", "N/A"))
        m2.metric("Reliability", health.get("reliability", "N/A"))
        m3.metric("Target Drift Score", health.get("target_drift", "N/A"))
        m4.metric("Est. Revenue Risk", financials.get("risk_amount", "N/A"))

        st.caption(
            f"Target stattest used: {meta.get('target_stattest', 'N/A')} · "
            f"Target column tracked: {meta.get('target_drift_tracked', 'N/A')}"
        )

        st.subheader("📊 Feature Drift Leaderboard")
        leaderboard = data.get("leaderboard", [])
        if leaderboard:
            df = pd.DataFrame(leaderboard)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No leaderboard data returned.")

        rigor = data.get("rigor", {})
        fairness_issues = rigor.get("fairness", [])
        st.subheader("⚖️ Fairness Check")
        if fairness_issues:
            st.error(f"{len(fairness_issues)} disparate impact issue(s) detected:")
            st.dataframe(pd.DataFrame(fairness_issues), use_container_width=True)
        else:
            st.success("No disparate impact detected across checked groups.")

        p_values = rigor.get("p_values", [])
        if p_values:
            with st.expander("Statistically significant feature shifts (KS test, p < 0.05)"):
                st.dataframe(pd.DataFrame(p_values), use_container_width=True)

else:
    st.info("Upload both a reference and a current CSV to run an analysis.")