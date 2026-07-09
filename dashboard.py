import os
import json
import pandas as pd
import streamlit as st


# Set up premium UI page configurations
st.set_page_config(
    page_title="Lead Intelligence Platform - Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title & Description
st.markdown("""
<div style="background-color:#1E1E2F;padding:20px;border-radius:12px;margin-bottom:25px;">
    <h1 style="color:#FFFFFF;margin:0;">📊 Lead Intelligence Platform</h1>
    <p style="color:#A0A0B0;margin:5px 0 0 0;font-size:16px;">Real-time execution dashboard, coverage metrics tracking, and tool runtime profiles.</p>
</div>
""", unsafe_allow_html=True)

# Load CSV Results
results_path = "data/results.csv"
history_path = "data/benchmark_history.json"

if not os.path.exists(results_path):
    st.warning(f"⚠️ Results data file '{results_path}' not found yet. Run a batch process first to generate analytics.")
    st.info("Run `leadresearch process` or `leadresearch benchmark` in your terminal to start gathering lead data.")
else:
    # 1. Read Lead Results Dataset
    df = pd.read_csv(results_path)
    
    # 2. Setup Top-level KPI cards
    total_processed = len(df)
    success_df = df[df["Status"] == "completed"]
    failures_df = df[df["Status"] == "failed"]
    
    avg_confidence = df["Confidence"].mean() if "Confidence" in df else 0.0
    avg_runtime = df["Runtime"].mean() if "Runtime" in df else 0.0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(label="Processed Brands", value=total_processed)
    with col2:
        st.metric(label="Success Leads", value=len(success_df), delta=f"{len(success_df)/total_processed*100:.1f}%" if total_processed else "0%")
    with col3:
        st.metric(label="Failures", value=len(failures_df))
    with col4:
        st.metric(label="Avg Confidence", value=f"{avg_confidence:.2f}")
    with col5:
        st.metric(label="Avg Runtime", value=f"{avg_runtime:.1f}s")
        
    st.markdown("---")
    
    # 3. Main content area: Coverage splits
    left_col, right_col = st.columns(2)
    
    with left_col:
        st.subheader("🎯 Lead Attributes Coverage")
        
        # Calculate coverage percentages
        website_cov = (df["Website"].notna() & (df["Website"] != "unknown")).sum() / total_processed * 100
        email_cov = df["Emails"].notna().sum() / total_processed * 100
        phone_cov = df["Phones"].notna().sum() / total_processed * 100
        address_cov = df["Addresses"].notna().sum() / total_processed * 100
        linkedin_cov = df["LinkedIn"].notna().sum() / total_processed * 100
        bp_maps_cov = df["Google Maps"].notna().sum() / total_processed * 100
        
        coverage_data = {
            "Attribute": ["Website", "Email", "Phone", "Address", "LinkedIn", "Google Maps/Business Profile"],
            "Coverage %": [website_cov, email_cov, phone_cov, address_cov, linkedin_cov, bp_maps_cov]
        }
        cov_df = pd.DataFrame(coverage_data)
        st.bar_chart(cov_df.set_index("Attribute"))
        
    with right_col:
        st.subheader("📈 Coverage Over Time (Commits)")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    
                if history_data:
                    hist_df = pd.DataFrame(history_data)
                    # Pivot or set index for multi-line plotting
                    hist_df["label"] = hist_df["commit"].astype(str) + " (" + hist_df["timestamp"].str[-8:] + ")"
                    chart_df = hist_df[["label", "website", "email", "phone", "address"]].set_index("label")
                    st.line_chart(chart_df)
                else:
                    st.info("No timeline history entries found in checkpoint.")
            except Exception as he:
                st.error(f"Failed to render coverage timeline graph: {he}")
        else:
            st.info("Run history file benchmark_history.json not found yet.")

    # 4. Leads Data Explorer
    st.subheader("🔍 Harvester Leads Explorer")
    st.dataframe(df, use_container_width=True)
