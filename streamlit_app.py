import streamlit as st
import time
from datetime import datetime
from intelligence_hub.ui.styles import get_custom_css
from intelligence_hub.core.mock_data import get_company_data
from intelligence_hub.graph.workflow import create_graph  # Real-Time Backend
from intelligence_hub.ui.components import (
    render_header,
    render_progress_chain,
    render_company_profile,
    render_financials_detailed,
    render_chart,
    render_competitors,
    render_insights_strategic,
    render_sources,
    render_pdf_analysis,
)

# --- Page Configuration ---
st.set_page_config(
    page_title="CorporateIntelligenceX",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Apply Custom CSS ---
st.markdown(get_custom_css(), unsafe_allow_html=True)

# --- Session State ---
if "logs" not in st.session_state:
    st.session_state.logs = [
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Intelligence Hub Initialized.",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Connected to Vector DB (Pinecone).",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Ready for Entity Query...",
    ]
if "data" not in st.session_state:
    st.session_state.data = None
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "progress_stage" not in st.session_state:
    st.session_state.progress_stage = 0


# --- Helper to append logs ---
def add_log(agent_name, action):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] **{agent_name}**: {action}"
    st.session_state.logs.append(log_entry)


# --- Wrapper to Simulate/Fetch Data ---
# --- Main App Logic ---
# --- Main App Logic ---


# Cache the Agent Graph to avoid re-initialization overhead (DB connections etc)
@st.cache_resource
def get_cached_graph():
    return create_graph()


def run_investigation(query):
    # Reset State
    st.session_state.logs = []
    st.session_state.analysis_complete = False
    st.session_state.progress_stage = 0

    # 1. Initialize Baseline (Hybrid Approach)
    base_data = get_company_data(query)
    st.session_state.data = base_data

    # 2. Run Real-Time Graph
    graph = get_cached_graph()

    with st.status("🚀 Orchestrating Intelligent Agents...", expanded=True) as status:
        st.write("🔌 Connecting to Agent Graph...")

        # Stream the Graph execution for instant feedback
        stream = graph.stream({"query": query, "logs": []})

        final_state = {}
        processed_logs = set()  # Track unique logs to avoid dupes in UI

        for event in stream:
            # Event corresponds to a node finishing
            for node, state in event.items():
                final_state = state  # Keep updating final state

                # Check for new logs
                current_logs = state.get("logs", [])
                for log in current_logs:
                    if log not in processed_logs:
                        processed_logs.add(log)

                        # UI Logic for Logs and Progress
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

        # 4. Update Data with Real Intelligence (Using final state)
        if final_state.get("financial_data"):
            real_data = final_state["financial_data"]

            # A. Update Financials
            if "financials" in real_data:
                real_fin = real_data["financials"]
                # Map Revenue
                if "revenue" in real_fin:
                    val = real_fin["revenue"]
                    st.session_state.data["financials"]["current"]["rev"] = (
                        f"AED {val/1_000_000_000:.1f}B"
                        if val > 1e9
                        else f"AED {val:,.0f}"
                    )
                # Map Profit
                if "net_income" in real_fin:  # Scrapers might use net_income
                    val = real_fin["net_income"]
                    st.session_state.data["financials"]["current"]["profit"] = (
                        f"AED {val/1_000_000_000:.1f}B"
                        if val > 1e9
                        else f"AED {val:,.0f}"
                    )

            # B. Update Profile (if Wiki scraped)
            if "profile" in real_data:
                prof = real_data["profile"]
                if "profile" not in st.session_state.data:
                    st.session_state.data["profile"] = {}  # Initialize if missing

                if "description" in prof:
                    st.session_state.data["profile"]["description"] = prof[
                        "description"
                    ]
                if "sector" in prof:
                    st.session_state.data["profile"]["sector"] = prof["sector"]

            # C. Update Sources
            if "sources" in real_data:
                st.session_state.data["sources"] = real_data["sources"]

        if final_state.get("insights"):
            st.session_state.data["insights"] = final_state["insights"]

        status.update(
            label="✅ **Investigation Complete**", state="complete", expanded=False
        )
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
    query_input = st.text_input(
        "Search Entity",
        placeholder="Enter Company Name or Ticker (e.g., 'Emaar', 'Emirates NBD')...",
        label_visibility="collapsed",
    )
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
elif (
    query_input and not st.session_state.analysis_complete
):  # Allow Enter key if simple
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
    # 5. Sources
    render_sources(data)

    st.markdown("---")

    # 6. PDF Analysis
    render_pdf_analysis(data)

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
