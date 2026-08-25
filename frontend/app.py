"""
Streamlit Frontend for Autonomous Data Analyst Agent.
"""
import streamlit as st
import requests
import base64
from PIL import Image
import io

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Autonomous Data Analyst Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich modern UI
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #E8FF8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .trace-node {
        font-size: 0.85rem;
        background-color: #1E293B;
        border-left: 3px solid #3B82F6;
        padding: 0.4rem 0.8rem;
        margin-bottom: 0.4rem;
        border-radius: 4px;
        color: #E2E8F0 !important;
    }
    .trace-node b {
        color: #60A5FA !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🤖 Autonomous Data Analyst Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Ask plain-English questions over CSV/Excel data — SQL generation, safe execution, auto-charts, and business summaries.</div>', unsafe_allow_html=True)

# Sidebar - Dataset Upload & Info
with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx", "xls"])
    
    use_sample = st.checkbox("Or use bundled sample sales dataset", value=False)
    
    if st.button("🚀 Load Dataset", type="primary", use_container_width=True):
        dataset_id = None
        if use_sample:
            with open("data/sample_dataset.csv", "rb") as f:
                files = {"file": ("sample_dataset.csv", f, "text/csv")}
                res = requests.post(f"{BACKEND_URL}/upload", files=files)
                if res.status_code == 200:
                    data = res.json()
                    dataset_id = data["dataset_id"]
                    st.session_state["dataset_id"] = dataset_id
                    st.session_state["tables"] = data["tables"]
                    st.success(f"Loaded Sample Data! ID: {dataset_id}")
                else:
                    st.error(f"Failed to load sample dataset: {res.text}")
        elif uploaded_file is not None:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            res = requests.post(f"{BACKEND_URL}/upload", files=files)
            if res.status_code == 200:
                data = res.json()
                dataset_id = data["dataset_id"]
                st.session_state["dataset_id"] = dataset_id
                st.session_state["tables"] = data["tables"]
                st.success(f"Uploaded! Dataset ID: {dataset_id}")
            else:
                st.error(f"Upload failed: {res.text}")
        else:
            st.warning("Please upload a file or select sample dataset.")

        # Automatically fetch profiling data on dataset load
        if dataset_id:
            try:
                prof_res = requests.get(f"{BACKEND_URL}/profile/{dataset_id}")
                if prof_res.status_code == 200:
                    st.session_state["profile"] = prof_res.json()
            except Exception as e:
                st.warning(f"Could not load profiling data: {e}")

    if "dataset_id" in st.session_state:
        st.divider()
        st.info(f"**Active Dataset ID:** `{st.session_state['dataset_id']}`\n\n**Tables:** {', '.join(st.session_state.get('tables', []))}")
        
        if "profile" in st.session_state:
            prof = st.session_state["profile"]
            st.metric("Dataset Quality Score", f"{prof['overall_quality_score']} / 100")

# Tabs: Agent Studio vs Data Profiling vs Observability Dashboard
tab_chat, tab_profile, tab_metrics = st.tabs([
    "💬 Agent Chat Studio", 
    "🔍 Data Quality & Profiling", 
    "📊 Observability & Metrics"
])

with tab_chat:
    if "dataset_id" not in st.session_state:
        st.info("👈 Please load a dataset from the sidebar to begin asking questions.")
    else:
        # Quick suggestion buttons
        st.write("**Suggested Questions:**")
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            if st.button("Total sales by category?"):
                st.session_state["question_input"] = "What is the total sales amount by product category?"
        with col_q2:
            if st.button("Top 3 products by sales?"):
                st.session_state["question_input"] = "Which are the top 3 products by sales amount?"
        with col_q3:
            if st.button("Sales breakdown by region?"):
                st.session_state["question_input"] = "Show me the sales breakdown by region with total quantity."

        question = st.text_input(
            "Ask a question about your data:",
            key="question_input",
            placeholder="e.g. What is the average sales amount per region?"
        )
        
        if st.button("Ask Agent", type="primary"):
            if not question.strip():
                st.warning("Please enter a question.")
            else:
                with st.spinner("🤖 Agent is planning, generating SQL, executing, and summarizing..."):
                    payload = {
                        "dataset_id": st.session_state["dataset_id"],
                        "question": question
                    }
                    try:
                        resp = requests.post(f"{BACKEND_URL}/ask", json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            
                            # Render Executive Summary
                            st.subheader("💡 Executive Business Summary")
                            st.write(data["summary"])

                            # Render Agent Analysis Plan
                            if data.get("plan"):
                                plan_info = data["plan"]
                                with st.expander("🎯 Agent Strategy & Decomposed Analysis Plan", expanded=True):
                                    st.markdown(f"**Intent:** {plan_info.get('intent', 'N/A')}")
                                    
                                    p1, p2, p3 = st.columns(3)
                                    p1.markdown(f"**Metrics:** `{', '.join(plan_info.get('metrics', [])) or 'None'}`")
                                    p2.markdown(f"**Dimensions:** `{', '.join(plan_info.get('dimensions', [])) or 'None'}`")
                                    p3.markdown(f"**Operations:** `{', '.join(plan_info.get('operations', [])) or 'None'}`")
                                    
                                    if plan_info.get("chart_type_suggestion"):
                                        st.markdown(f"**Recommended Visual:** `{plan_info.get('chart_type_suggestion')}`")

                                    st.markdown("**Execution Strategy Steps:**")
                                    for step in plan_info.get("steps", []):
                                        st.markdown(f"- {step}")

                            # Render Chart if present
                            if data.get("chart_base64"):
                                st.subheader("📈 Generated Visualization")
                                img_bytes = base64.b64decode(data["chart_base64"])
                                image = Image.open(io.BytesIO(img_bytes))
                                st.image(image, use_container_width=True)
                                
                            # Render SQL Query
                            st.subheader("🔍 Generated SQL Query")
                            if data.get("sql"):
                                st.code(data["sql"], language="sql")
                            else:
                                st.write("No SQL query generated.")
                                
                            # Render Agent Execution Trace
                            with st.expander("🕵️ Agent Observability Trace"):
                                st.write(f"**Retries Taken:** {data.get('retries', 0)}")
                                for step in data.get("trace", []):
                                    st.markdown(
                                        f'<div class="trace-node"><b>[{step["node"]}]</b> {step["detail"]}</div>',
                                        unsafe_allow_html=True
                                    )
                        else:
                            st.error(f"Error from server: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to communicate with backend: {e}")

with tab_profile:
    st.header("🔍 Automated Dataset Profiling & Data Quality")
    if "dataset_id" not in st.session_state:
        st.info("👈 Please load a dataset from the sidebar to view automated profiling and data quality analytics.")
    else:
        if st.button("🔄 Refresh Dataset Profile"):
            try:
                prof_res = requests.get(f"{BACKEND_URL}/profile/{st.session_state['dataset_id']}")
                if prof_res.status_code == 200:
                    st.session_state["profile"] = prof_res.json()
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to refresh profile: {e}")

        if "profile" in st.session_state:
            prof = st.session_state["profile"]

            # Overview Cards
            m1, m2, m3, m4 = st.columns(4)
            score = prof['overall_quality_score']
            badge = "🟢 High Quality" if score >= 85 else ("🟡 Moderate Warnings" if score >= 65 else "🔴 Quality Issues Detected")
            m1.metric("Overall Quality Score", f"{score} / 100", delta=badge)
            m2.metric("Total Tables", len(prof['tables']))
            m3.metric("Total Rows", f"{prof['total_rows']:,}")
            m4.metric("Total Columns", prof['total_columns'])

            st.divider()

            # Data Quality Alerts
            st.subheader("🚨 Data Quality & Health Warnings")
            if prof.get("warnings"):
                for warn in prof["warnings"]:
                    st.warning(warn)
            else:
                st.success("🎉 No data quality issues or warnings detected in dataset!")

            st.divider()

            # Table Details & Column Profiles
            st.subheader("📋 Table & Schema Deep-Dive")
            for t in prof.get("tables", []):
                with st.expander(f"Table: `{t['table_name']}` ({t['row_count']:,} rows, {t['column_count']} columns | Quality: {t['quality_score']}/100)", expanded=True):
                    if t.get("duplicate_rows", 0) > 0:
                        st.caption(f"⚠️ **Duplicate Rows:** {t['duplicate_rows']:,}")
                    
                    # Columns table view
                    cols_data = []
                    for c in t.get("columns", []):
                        flags = []
                        if c["is_candidate_pk"]:
                            flags.append("🔑 Candidate Key")
                        if c["is_datetime"]:
                            flags.append("📅 Datetime")
                        if c["null_count"] > 0:
                            flags.append(f"⚠️ {c['null_percentage']}% Null")

                        cols_data.append({
                            "Column": c["name"],
                            "Type": c["data_type"],
                            "Nulls": f"{c['null_count']} ({c['null_percentage']}%)",
                            "Unique Values": c["distinct_count"],
                            "Sample Values": ", ".join(c["sample_values"]),
                            "Min / Max": f"{c['min_val']} / {c['max_val']}" if c["min_val"] is not None else "-",
                            "Mean": c["mean_val"] if c["mean_val"] is not None else "-",
                            "Flags": " | ".join(flags) if flags else "✅ Clean"
                        })

                    st.dataframe(cols_data, use_container_width=True)

with tab_metrics:
    st.header("📊 Real-time Observability Dashboard")
    if st.button("🔄 Refresh Metrics"):
        st.rerun()
        
    try:
        stats_resp = requests.get(f"{BACKEND_URL}/stats")
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Runs", stats["total_runs"])
            c2.metric("Success Rate", f"{stats['success_rate']}%")
            c3.metric("Avg Latency", f"{stats['avg_latency_seconds']} s")
            c4.metric("Avg Retries", stats["avg_retries"])
            
            st.divider()
            st.subheader("⚠️ Recent Failures Log")
            if stats["recent_failures"]:
                st.dataframe(stats["recent_failures"], use_container_width=True)
            else:
                st.success("No failed runs recorded!")
        else:
            st.error("Failed to load metrics.")
    except Exception as e:
        st.error(f"Backend not reachable: {e}")

