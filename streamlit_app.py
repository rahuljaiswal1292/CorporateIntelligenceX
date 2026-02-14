import streamlit as st
import time
from datetime import datetime
import os
from pathlib import Path
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
    render_references,
)

image_path = os.path.join(
    os.path.dirname(__file__), "intelligence_hub", "ui", "favicon.jpg"
)

# --- Page Configuration ---
st.set_page_config(
    page_title="CorporateIntelligenceX",
    page_icon=image_path,
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Apply Custom CSS ---
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Load additional custom CSS from file
custom_css_path = Path(__file__).parent / "intelligence_hub" / "ui" / "custom_styles.css"
if custom_css_path.exists():
    with open(custom_css_path, 'r', encoding='utf-8') as f:
        custom_css = f"<style>{f.read()}</style>"
        st.markdown(custom_css, unsafe_allow_html=True)

# --- Session State ---
if "logs" not in st.session_state:
    st.session_state.logs = [
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Intelligence Hub Initialized.",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Connected to Vector DB (ChromaDB).",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Ready for Entity Query...",
    ]
if "data" not in st.session_state:
    st.session_state.data = None
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "progress_stage" not in st.session_state:
    st.session_state.progress_stage = 0
if "canonical_name" not in st.session_state:
    st.session_state.canonical_name = None
if "abort_investigation" not in st.session_state:
    st.session_state.abort_investigation = False
if "is_resolving" not in st.session_state:
    st.session_state.is_resolving = False
if "confidence_score" not in st.session_state:
    st.session_state.confidence_score = None
if "search_history" not in st.session_state:
    st.session_state.search_history = []


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
    st.session_state.canonical_name = None
    st.session_state.confidence_score = None
    st.session_state.abort_investigation = False
    st.session_state.is_resolving = True
    
    # Add to search history (keep last 3)
    if query not in st.session_state.search_history:
        st.session_state.search_history.insert(0, query)
        st.session_state.search_history = st.session_state.search_history[:3]

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
            # Check if user requested abort
            if st.session_state.abort_investigation:
                st.warning("⚠️ Investigation aborted by user")
                status.update(label="❌ **Investigation Aborted**", state="error", expanded=False)
                return
            
            # Event corresponds to a node finishing
            for node, state in event.items():
                final_state = state  # Keep updating final state
                
                # Capture canonical name from state if available
                if state.get("canonical_name") and not st.session_state.canonical_name:
                    st.session_state.canonical_name = state["canonical_name"]
                    # Capture confidence score if available
                    if state.get("confidence") or state.get("confidence_score"):
                        confidence = state.get("confidence") or state.get("confidence_score")
                        st.session_state.confidence_score = round(confidence) if isinstance(confidence, (int, float)) else None
                    st.session_state.is_resolving = False

                # Check for new logs
                current_logs = state.get("logs", [])
                for log in current_logs:
                    if log not in processed_logs:
                        processed_logs.add(log)

                        # UI Logic for Logs and Progress
                        if "Resolved" in log:
                            add_log("Resolver", log)
                            st.session_state.progress_stage = 1  # Canonical Resolution
                            st.write(f"✅ {log}")
                            # Extract canonical name from log if not already set
                            if " to " in log and not st.session_state.canonical_name:
                                parts = log.split(" to ")
                                if len(parts) > 1:
                                    st.session_state.canonical_name = parts[1].strip()
                                    st.session_state.is_resolving = False
                        elif "SERP" in log or "Profiling" in log:
                            add_log("SERP Agent", log)
                            st.session_state.progress_stage = 2  # SERP Profiling
                            st.write(f"🔍 {log}")
                        elif "Scraping" in log:
                            add_log("Scraper", log)
                            st.session_state.progress_stage = 3  # Scrape
                            st.write(f"🕸️ {log}")
                        elif "Vectorizer" in log:
                            add_log("Vectorizer", log)
                            st.session_state.progress_stage = 4  # Vectorize
                            st.write(f"🧠 {log}")
                        elif "Analyst" in log:
                            add_log("Analyst", log)
                            st.session_state.progress_stage = 5  # Analyze
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
    st.markdown(
        """
        <h3 style='text-align: center; padding-bottom: 5px;'>
            CorporateIntelligenceX
        </h3>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
    <div style="text-align: center; color: rgba(250, 250, 250, 0.6); font-size: 1rem; line-height: 1.5;">
        📡 Agent Pulse
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='display: flex; justify-content: center; width: 100%;'><a id='lang_smith_link' href='https://smith.langchain.com/o/161479c6-ccc7-4a79-ab5b-8142f6f7ffa0/projects/p/c3f23a4a-4ff5-4202-b429-75fcc1fc0bff?timeModel=%7B%22duration%22%3A%227d%22%7D'>Live Agent Trace</a></div>",
        unsafe_allow_html=True,
    )

    st.markdown("#### Agent Logs")
    log_container = st.container(height=400)
    with log_container:
        for log in reversed(st.session_state.logs):
            st.markdown(log)

    st.markdown("---")
    st.caption(f"System Status: **ONLINE**")
    st.caption(f"Vector DB: **ChromaDB**")
    st.caption(f"Model: **GPT-4-turbo**")

# --- Main Layout ---
# Banner with styled heading and tagline (matching reference)
st.markdown(
    """
    <div class="main-banner">
        <h1 class="main-heading">CorporateIntelligenceX</h1>
        <p class="main-tagline">A smart GenAI-powered corporate information profiler.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Feature tiles below banner
st.html(
    """
    <div class="feature-grid">
        <div class="feature-card">
            <h3>🤖 Multi-Agent AI</h3>
            <p>Specialized AI agents work in parallel for different analysis tasks</p>
        </div>
        <div class="feature-card">
            <h3>⚡ Real-time Updates</h3>
            <p>Live streaming of search progress with instant notifications</p>
        </div>
        <div class="feature-card">
            <h3>🌐 Data Integration</h3>
            <p>Multiple data sources for comprehensive and accurate insights</p>
        </div>
        <div class="feature-card">
            <h3>📊 Advanced Analytics</h3>
            <p>Deep insights, trend analysis, and predictive intelligence</p>
        </div>
    </div>
    """
)

# Search Company Label (matching reference)
st.markdown(
    '<div class="section-heading">🔍 Search or Select Company</div>',
    unsafe_allow_html=True
)

# Input Box with inline buttons
col_input, col_search, col_clear = st.columns([6, 2, 2])

with col_input:
    query_input = st.text_input(
        "Search Entity",
        placeholder="Enter company name e.g., Tesla, Emirates NBD, ADNOC, Dubai Islamic Bank...",
        label_visibility="collapsed",
        key="company_search_input"
    )

with col_search:
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True, key="search_button")

with col_clear:
    abort_clicked = st.button("🛑 Abort", type="secondary", use_container_width=True, key="abort_button_main")

# Recent Searches Section
if st.session_state.search_history:
    st.markdown('<div style="margin-top: 12px; margin-bottom: 12px; font-size: 13px; color: #64748b;">Recent Searches:</div>', unsafe_allow_html=True)
    
    # Display as clickable chips
    cols = st.columns(len(st.session_state.search_history))
    for idx, search_term in enumerate(st.session_state.search_history):
        with cols[idx]:
            if st.button(f"🕒 {search_term}", key=f"recent_{idx}", use_container_width=True):
                st.session_state.company_search_input = search_term
                run_investigation(search_term)
                st.rerun()

# Render Progress Chain (Below recent searches)
with st.expander("📊 Investigation Progress Pipeline", expanded=True):
    render_progress_chain(st.session_state.progress_stage)

# Canonical Name Label (always visible) - Reduced size
st.markdown(
    '<div style="margin-top: 12px; margin-bottom: 6px; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.03em;">Resolved Company Name</div>',
    unsafe_allow_html=True
)

# Canonical Name Display
if st.session_state.is_resolving or st.session_state.canonical_name:
    # Determine state and display
    if st.session_state.is_resolving and not st.session_state.canonical_name:
        # Resolving state with blinking effect
        st.markdown(
            """
            <div class="canonical-container">
                <div class="canonical-label">
                    <span class="canonical-icon">🏢</span>
                    <span class="canonical-title">RESOLVED COMPANY NAME</span>
                </div>
                <div class="canonical-value resolving">
                    <span class="canonical-text">Resolving...</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.canonical_name and st.session_state.analysis_complete:
        # Resolved state with checkmark and confidence score
        confidence_display = f" (Confidence: {st.session_state.confidence_score}%)" if st.session_state.confidence_score else ""
        st.markdown(
            f"""
            <div class="canonical-container">
                <div class="canonical-label">
                    <span class="canonical-icon">🏢</span>
                    <span class="canonical-title">RESOLVED COMPANY NAME</span>
                </div>
                <div class="canonical-value resolved">
                    <span class="canonical-text">{st.session_state.canonical_name}{confidence_display}</span>
                    <span class="canonical-check">✓</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.canonical_name:
        # In progress (name resolved but analysis not complete)
        confidence_display = f" (Confidence: {st.session_state.confidence_score}%)" if st.session_state.confidence_score else ""
        st.markdown(
            f"""
            <div class="canonical-container">
                <div class="canonical-label">
                    <span class="canonical-icon">🏢</span>
                    <span class="canonical-title">RESOLVED COMPANY NAME</span>
                </div>
                <div class="canonical-value resolved">
                    <span class="canonical-text">{st.session_state.canonical_name}{confidence_display}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    # Default state - ready to search
    st.markdown(
        """
        <div class="canonical-container">
            <div class="canonical-label">
                <span class="canonical-icon">🏢</span>
                <span class="canonical-title">RESOLVED COMPANY NAME</span>
            </div>
            <div class="canonical-value">
                <span class="canonical-text">Ready to search</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

if abort_clicked:
    # Set abort flag FIRST to stop ongoing workflow
    st.session_state.abort_investigation = True
    
    # Then clear all state
    st.session_state.data = None
    st.session_state.logs = []
    st.session_state.progress_stage = 0
    st.session_state.analysis_complete = False
    st.session_state.canonical_name = None
    st.session_state.confidence_score = None
    st.session_state.is_resolving = False
    
    # Add log message
    add_log("System", "Investigation aborted by user")
    
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

    st.markdown("---")

    # 7. References & Sources
    render_references(data)

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
