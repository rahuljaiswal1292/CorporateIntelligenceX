import streamlit as st
import time
from datetime import datetime
from intelligence_hub.ui.styles import get_custom_css
from intelligence_hub.core.mock_data import get_company_data
from intelligence_hub.graph.workflow import create_graph # Real-Time Backend
from intelligence_hub.ui.components import (
    render_header,
    render_progress_chain,
    render_company_profile,
    render_financials_detailed,
    render_chart,
    render_competitors,
    render_insights_strategic, 
    render_sources
)

# --- Page Configuration ---
st.set_page_config(
    page_title="CorporateIntelligenceX",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Apply Custom CSS ---
st.markdown(get_custom_css(), unsafe_allow_html=True)

# --- Session State ---
if 'logs' not in st.session_state:
    st.session_state.logs = [
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Intelligence Hub Initialized.",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Connected to Vector DB (Pinecone).",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Ready for Entity Query..."
    ]
if 'data' not in st.session_state:
    st.session_state.data = None
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'progress_stage' not in st.session_state:
    st.session_state.progress_stage = 0

# --- Helper to append logs ---
def add_log(agent_name, action):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] **{agent_name}**: {action}"
    st.session_state.logs.append(log_entry)

# --- Wrapper to Simulate/Fetch Data ---
# --- Main App Logic ---
def run_investigation(query):
    # Reset State
    st.session_state.logs = []
    st.session_state.analysis_complete = False
    st.session_state.progress_stage = 0
    
    # 1. Initialize Baseline (Hybrid Approach)
    # We fetch the mock structure to ensure charts/competitors tables have data structure
    # The Agents will then OVERRIDE the specifics (Financials, Insights).
    base_data = get_company_data(query) 
    st.session_state.data = base_data
    
    # 2. Run Real-Time Graph
    graph = create_graph()
    
    with st.status("🚀 Orchestrating Intelligent Agents...", expanded=True) as status:
        st.write("🔌 Connecting to Agent Graph...")
        
        # Invoke Graph (Synchronous for now)
        final_state = graph.invoke({"query": query, "logs": []})
        
        # 3. Process Result & Logs from Graph
        for log in final_state.get("logs", []):
            if "Resolved" in log:
                add_log("Resolver", log)
                st.session_state.progress_stage = 1
                st.write(f"✅ {log}")
            elif "Scraping" in log:
                 add_log("Scraper", log)
                 st.session_state.progress_stage = 2
                 st.write(f"🕸️ {log}")
            elif "Vectorizer" in log:
                 add_log("Vectorizer", log)
                 st.session_state.progress_stage = 3
                 st.write(f"🧠 {log}")
            elif "Analyst" in log:
                 add_log("Analyst", log)
                 st.session_state.progress_stage = 4
                 st.write(f"📊 {log}")
            else:
                 add_log("System", log)
            time.sleep(0.3) # Interactive Delay
            
        # 4. Update Data with Real Intelligence
        if final_state.get("financial_data"):
             real_fin = final_state["financial_data"]
             # Update Base Data with Real Values
             if "revenue" in real_fin:
                 # Format nicely
                 rev_val = real_fin['revenue']
                 rev_fmt = f"AED {rev_val/1_000_000_000:.1f}B" if rev_val > 1_000_000 else f"AED {rev_val:,.0f}"
                 st.session_state.data["financials"]["current"]["rev"] = rev_fmt
                 
             if "profit" in real_fin:
                 prof_val = real_fin['profit']
                 prof_fmt = f"AED {prof_val/1_000_000_000:.1f}B" if prof_val > 1_000_000 else f"AED {prof_val:,.0f}"
                 st.session_state.data["financials"]["current"]["profit"] = prof_fmt

        if final_state.get("insights"):
            st.session_state.data["insights"] = final_state["insights"]
        
        status.update(label="✅ **Investigation Complete**", state="complete", expanded=False)
        st.session_state.analysis_complete = True

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🏦 CorporateIntelligenceX") 
    st.caption("AI-Powered Banking Profiler")
    
    st.markdown("### 📡 Live Agent Trace")
    log_container = st.container(height=400)
    with log_container:
        for log in reversed(st.session_state.logs):
            st.markdown(log)
    
    st.markdown("---")
    st.caption(f"System Status: **ONLINE**")
    st.caption(f"Vector DB: **Pinecone**")
    st.caption(f"Model: **Gemini 1.5 Pro**")

# --- Main Layout ---
# --- Main Layout ---
render_header()

# Search Area with ENBD Styling
c_search, c_btn, c_clear = st.columns([6, 1, 1])
with c_search:
    query_input = st.text_input("Search Entity", placeholder="Enter Company Name or Ticker (e.g., 'Emaar', 'Emirates NBD')...", label_visibility="collapsed")
with c_btn:
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)
with c_clear:
    clear_clicked = st.button("❌ Clear", use_container_width=True)

if clear_clicked:
    st.session_state.data = None
    st.session_state.logs = []
    st.session_state.progress_stage = 0
    st.session_state.analysis_complete = False
    st.rerun()

# Trigger Search
if search_clicked and query_input:
    run_investigation(query_input)
    st.rerun()
elif query_input and not st.session_state.analysis_complete: # Allow Enter key if simple
    # logic to handle enter key is tricky with text_input without form, 
    # but sidebar search button is explicit. 
    # Let's rely on the button for the "Deep Search" feel requested.
    pass

# Render Progress Chain
if st.session_state.progress_stage > 0:
    render_progress_chain(st.session_state.progress_stage)

if st.session_state.analysis_complete and st.session_state.data:
    data = st.session_state.data
    
    # 1. Company Profile
    render_company_profile(data)
    
    # 2. Financials (Detailed)
    render_financials_detailed(data)
    
    # 3. Charts & Competitors (Stacked Layout)
    render_chart(data)
    
    st.markdown("---")
    
    render_competitors(data)
    
    st.markdown("---")
    
    # 4. Strategic Insights (Full Width / Prominent)
    render_insights_strategic(data)
    
    st.markdown("---")
    
    # 5. Sources
    render_sources(data)

elif not st.session_state.analysis_complete and st.session_state.progress_stage == 0:
    # Empty State - Dashboard View
    st.subheader("Recent Investigations")
    col_a, col_b, col_c = st.columns(3)
    if col_a.button("Emaar Properties", use_container_width=True):
        run_investigation("Emaar")
        st.rerun()
    if col_b.button("Emirates NBD", use_container_width=True):
        run_investigation("Emirates NBD")
        st.rerun()
    if col_c.button("Air Arabia", use_container_width=True):
        run_investigation("Air Arabia")
        st.rerun()
