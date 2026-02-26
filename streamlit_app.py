import streamlit as st
import asyncio
import sys

# Windows-specific fix for Playwright/asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import time
from datetime import datetime
import textwrap
import os
import uuid
import base64
from pathlib import Path
from intelligence_hub.ui.styles import get_custom_css
from intelligence_hub.ui.dashboard import render_main_dashboard, get_test_dashboard_data
from intelligence_hub.ui.pipeline_viz import (
    render_agent_pipeline,
    get_default_agent_status,
)
from intelligence_hub.core.mock_data import get_company_data
from intelligence_hub.llm.models import LLMModel

# Force reload backend modules to pick up state changes
import sys
import importlib

if "intelligence_hub.graph.state" in sys.modules:
    importlib.reload(sys.modules["intelligence_hub.graph.state"])
if "intelligence_hub.graph.workflow" in sys.modules:
    importlib.reload(sys.modules["intelligence_hub.graph.workflow"])

from intelligence_hub.graph.workflow import (
    create_resolution_graph,
    create_enrichment_graph,
)  # Split Graphs
from intelligence_hub.ui.utils import get_image_base64, format_val, add_log
from intelligence_hub.ui.components import (
    render_header,
    render_company_profile,
    render_financials_detailed,
    render_chart,
    render_competitors,
    render_insights_strategic,
    render_sources,
    render_pdf_analysis,
    render_references,
    render_company_summary_card,
)
from intelligence_hub.ui.chat_ui import render_chatbot_panel


image_path = os.path.join(
    os.path.dirname(__file__), "intelligence_hub", "ui", "favicon.jpg"
)


# --- Deleted local get_image_base64 (now imported from utils) ---


logo_base64 = get_image_base64(
    image_path_ico := os.path.join(
        os.path.dirname(__file__), "intelligence_hub", "ui", "favicon.ico"
    )
)

# --- Page Configuration ---
st.set_page_config(
    page_title="CorporateIntelligenceX",
    page_icon=image_path_ico,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Apply Custom CSS ---
st.html(get_custom_css())

# Load additional custom CSS from file
custom_css_path = (
    Path(__file__).parent / "intelligence_hub" / "ui" / "custom_styles.css"
)
if custom_css_path.exists():
    with open(custom_css_path, "r", encoding="utf-8") as f:
        custom_css = f"<style>{f.read()}</style>"
        st.html(custom_css)

# --- Session State ---
if "logs" not in st.session_state:
    st.session_state.logs = [
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Intelligence Hub Initialized.",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Connected to Vector DB (ChromaDB).",
        f"[{datetime.now().strftime('%H:%M:%S')}] **System**: Ready for Entity Query...",
    ]
if "company_profile" not in st.session_state:
    st.session_state.company_profile = None
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
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "investigation_paused" not in st.session_state:
    st.session_state.investigation_paused = False
if "intermediate_state" not in st.session_state:
    st.session_state.intermediate_state = None
if "agent_status" not in st.session_state:
    st.session_state.agent_status = get_default_agent_status()
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "show_chatbot" not in st.session_state:
    st.session_state.show_chatbot = False
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False


# Removed local helpers (moved to intelligence_hub.ui.utils and components.py)


# Cache the Agent Graph to avoid re-initialization overhead (DB connections etc)
# Cache the Agent Graphs
@st.cache_resource(show_spinner=False)
def get_cached_resolution_graph_v6():
    return create_resolution_graph()


@st.cache_resource(show_spinner=False)
def get_cached_enrichment_graph_v6():
    return create_enrichment_graph()


def run_investigation(
    query_or_resume,
    pipeline_placeholder=None,
    resolved_placeholder=None,
    sidebar_logs_placeholder=None,
    dashboard_placeholder=None,
):
    resume_mode = False

    # Check if this is a new search or resume
    if query_or_resume is None or st.session_state.investigation_paused:
        resume_mode = True
        query = (
            st.session_state.data.get("query", "Unknown")
            if st.session_state.data
            else "Unknown"
        )
    else:
        query = query_or_resume
        # Reset State
        st.session_state.logs = []
        st.session_state.analysis_complete = False
        st.session_state.progress_stage = 0
        st.session_state.canonical_name = None
        st.session_state.confidence_score = None
        st.session_state.abort_investigation = False
        st.session_state.is_resolving = True  # Resolving starts now
        st.session_state.investigation_paused = False
        st.session_state.company_profile = None  # Clear old profile
        st.session_state.intermediate_state = None
        st.session_state.is_generating = False  # Reset generate flag
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.agent_status = get_default_agent_status()
        st.session_state.agent_status["master_agent"] = "running"

        # 1. Initialize Baseline (Hybrid Approach)
        base_data = get_company_data(query)
        st.session_state.data = base_data

    # UI Helpers
    def update_pipeline_ui():
        with pipeline_placeholder.container():
            # Use new pipeline visualization
            data = st.session_state.get("data", {})
            render_agent_pipeline(data, show_details=False)

    def update_resolved_ui():
        # Hide button during investigation to avoid duplicate key errors
        # Button will appear after st.rerun() in main app flow
        render_company_summary_card(
            resolved_placeholder,
            key="btn_continue_investigation_internal",
            show_button=False,
        )

    # Helper to update sidebar logs in real-time
    def update_sidebar_logs():
        if sidebar_logs_placeholder:
            html_buffer = []
            # Limit to recent logs to prevent huge payload if needed,
            # but user asked for "all logs". reversed() is efficient iterator.
            for log in reversed(st.session_state.logs):
                prefix_elem = ""
                message = log
                if ": " in log:
                    parts = log.split(": ", 1)
                    # Highlight the component name
                    prefix_elem = f'<span class="log-prefix">{parts[0]}</span>'
                    message = parts[1]

                html_buffer.append(
                    f'<div class="log-entry">{prefix_elem}<span class="log-content">{message}</span></div>'
                )

            full_html = f'<div class="log-scroller">{"".join(html_buffer)}</div>'
            sidebar_logs_placeholder.markdown(full_html, unsafe_allow_html=True)

    # Shadow global add_log to trigger sidebar updates
    def add_log(agent_name, action):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] **{agent_name}**: {action}"
        st.session_state.logs.append(log_entry)
        update_sidebar_logs()

    # 2. Select Graph & Input
    # Extract LLM config from session state (UI sliders)
    llm_config = {
        "model": st.session_state.get("llm_model_select", "gpt-4-turbo"),
        "temperature": st.session_state.get("llm_temperature", 0.0),
        "top_p": st.session_state.get("llm_top_p", 1.0),
        "frequency_penalty": st.session_state.get("llm_freq_penalty", 0.0),
    }

    if not resume_mode:
        graph = get_cached_resolution_graph_v6()
        input_data = {"query": query, "logs": [], "llm_config": llm_config}
        processed_logs = set()
    else:
        graph = get_cached_enrichment_graph_v6()
        input_data = st.session_state.intermediate_state
        # Update LLM config in case user changed settings before continuing
        input_data["llm_config"] = llm_config
        processed_logs = set(input_data.get("logs", []))
        # Mark master as done, set parallel agents to running
        st.session_state.agent_status["master_agent"] = "success"
        st.session_state.agent_status["wikipedia_agent"] = "running"
        st.session_state.agent_status["news_agent"] = "running"
        st.session_state.agent_status["ded_agent"] = "running"

    # 3. Setup Stream
    label = (
        "📝 Live System Logs (Enrichment)"
        if resume_mode
        else "📝 Live System Logs (Resolution)"
    )

    # Limit indentation changes by using a dummy block, or just unindent.
    # User wants to disable live logs.

    # Stream the Graph execution (Use thread_id for state persistence/checkpointing)
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    stream = graph.stream(input_data, config=config)
    final_state = input_data.copy() if not resume_mode else {}

    # Initial Pipeline Update
    update_pipeline_ui()
    update_resolved_ui()  # Initial Blink

    if not resume_mode:
        add_log(
            "System",
            f"Target identified: '{query}'. Orchestrating research sequence...",
        )
        add_log(
            "Master Agent", "Consulting internal Knowledge Graph & Entity Mappings..."
        )
        update_sidebar_logs()
    else:
        add_log("System", "Resuming investigation: Expanding intelligence footprint...")
        update_sidebar_logs()

    for event in stream:
        # Check if user requested abort
        if st.session_state.abort_investigation:
            st.warning("⚠️ Investigation aborted by user")
            # status.update removed
            return

        # Event corresponds to a node finishing
        for node, state in event.items():
            final_state = state  # Keep updating final state

            # --- 1. DATA EXTRACTION FIRST ---
            # Capture canonical name from state if available
            state_canonical = state.get("canonical_name") or state.get("company_name")

            # Ensure profile container exists
            if st.session_state.company_profile is None:
                st.session_state.company_profile = {}

            # Capture structured profile data (merging, not replacing)
            new_profile_data = state.get("enrichments") or state.get("data")
            if isinstance(new_profile_data, dict):
                st.session_state.company_profile.update(new_profile_data)

            # Capture top-level fields that contribute to the summary card
            for field in [
                "ticker",
                "exchange",
                "website",
                "description",
                "sector",
                "industry",
                "confidence",
                "confidence_score",
            ]:
                if field in state and state[field] is not None:
                    # Map 'confidence' to 'confidence_score' for card consistency
                    target_field = (
                        "confidence_score" if field == "confidence" else field
                    )
                    st.session_state.company_profile[target_field] = state[field]

            # A. CAPTURE CANONICAL NAME & CONFIDENCE (If available in this event)
            if state_canonical and not st.session_state.canonical_name:
                import re as _re

                # Strip any HTML tags (e.g. </div> from profiler output)
                clean_name = _re.sub(r"<[^>]+>", "", str(state_canonical)).strip()
                if clean_name:
                    st.session_state.canonical_name = clean_name

            # Sync Confidence Score if provided in this node's state
            if state.get("confidence") or state.get("confidence_score"):
                confidence = state.get("confidence") or state.get("confidence_score")
                st.session_state.confidence_score = (
                    round(confidence) if isinstance(confidence, (int, float)) else None
                )

            # B. SIGNAL COMPLETION OF PHASE 1 (Resolution + Profiling)
            # Only mark resolution phase as complete AFTER 'profiling' finishes
            if node == "profiling" or node == "resolution":
                # Wait for profiling specifically for the most complete card data
                if node == "profiling":
                    st.session_state.is_resolving = False
                    st.session_state.progress_stage = 2

            # --- 2. STATUS UPDATES SECOND ---
            # ---- Map LangGraph node to agent_status key ----
            node_to_agent = {
                "resolution": None,  # Keep master_agent 'running' during resolution
                "profiling": "master_agent",  # Only mark success after profiling completes
                "wikipedia": "wikipedia_agent",
                "news": "news_agent",
                "ded": "ded_agent",
                "scraper": "scraper",
                "vectorizer": "vectorizer",
                "pdf_agent": "pdf_agent",
                "analyst": "analyst",
                "start_enrichment": None,  # passthrough node
            }
            agent_key = node_to_agent.get(node)
            if agent_key:
                # Check if this node had an error
                node_logs = state.get("logs", [])
                last_log = node_logs[-1].lower() if node_logs else ""
                has_error = ("failed" in last_log and "error" in last_log) or (
                    "exception" in last_log
                )
                st.session_state.agent_status[agent_key] = (
                    "error" if has_error else "success"
                )

                # Set next sequential agents to "running" if master finished
                if node in ("wikipedia", "news", "ded", "scraper", "pdf_agent"):
                    # Mark the specific agent that finished as success
                    agent_map = {
                        "wikipedia": "wikipedia_agent",
                        "news": "news_agent",
                        "ded": "ded_agent",
                        "scraper": "scraper",
                        "pdf_agent": "pdf_agent",
                    }
                    if node in agent_map:
                        st.session_state.agent_status[agent_map[node]] = "success"
                        if node == "scraper":
                            st.session_state.agent_status["yahoo_agent"] = "success"

                elif node == "vectorizer":
                    st.session_state.agent_status["vectorizer"] = "success"
                elif node == "analyst":
                    st.session_state.agent_status["analyst"] = "success"
                    st.session_state.analysis_complete = True

            # Start Enrichment Phase (outside if agent_key because start_enrichment has None)
            if node == "start_enrichment":
                # Parallel Enrichment Phase: Start all tracks simultaneously (Visual)
                st.session_state.agent_status["wikipedia_agent"] = "running"
                st.session_state.agent_status["news_agent"] = "running"
                st.session_state.agent_status["ded_agent"] = "running"
                st.session_state.agent_status["scraper"] = "running"
                st.session_state.agent_status["yahoo_agent"] = "running"
                st.session_state.agent_status["pdf_agent"] = "running"

                # Smart Skip Handling: If Exchange is known, mark the other as "completed" immediately
                exchange_val = str(state.get("exchange", "")).upper()
                if exchange_val == "DFM":
                    st.session_state.agent_status["scraper"] = "success"
                elif exchange_val == "ADX":
                    st.session_state.agent_status["ded_agent"] = "success"

            # Check for new logs
            current_logs = state.get("logs", [])
            for log in current_logs:
                if log not in processed_logs:
                    processed_logs.add(log)

                    # UI Logic for Logs and Progress
                    if "Resolved" in log or "Canonical Name" in log:
                        add_log("Resolver", log)
                        st.session_state.progress_stage = 1  # Canonical Resolution

                        # Extract canonical name from log if not already set
                        if (
                            "Canonical Name: " in log
                            and not st.session_state.canonical_name
                        ):
                            parts = log.split("Canonical Name: ")
                            if len(parts) > 1:
                                import re as _re

                                raw_name = parts[1].strip()
                                clean_name = _re.sub(r"<[^>]+>", "", raw_name).strip()
                                if clean_name:
                                    st.session_state.canonical_name = clean_name
                                st.session_state.is_resolving = False

                                # Mark Stage 1 as Complete (Green) immediately
                                st.session_state.progress_stage = 2
                        elif " to " in log and not st.session_state.canonical_name:
                            parts = log.split(" to ")
                            if len(parts) > 1:
                                import re as _re

                                # Strip any HTML tags in case log contains markup
                                raw_name = parts[1].strip()
                                clean_name = _re.sub(r"<[^>]+>", "", raw_name).strip()
                                if clean_name:
                                    st.session_state.canonical_name = clean_name
                                st.session_state.is_resolving = False

                                # Mark Stage 1 as Complete (Green) immediately
                                st.session_state.progress_stage = 2
                    elif "SERP" in log or "Profiling" in log:
                        add_log("SERP Agent", log)
                        # Only set to 1 if we haven't advanced to later stages (Resolution Done = 2)
                        if st.session_state.progress_stage < 2:
                            st.session_state.progress_stage = 1  # Merged with Canonical
                    elif "Enrichment" in log or "Scraping" in log:
                        add_log("Harvester", log)
                        st.session_state.progress_stage = (
                            2  # Parallel Enrichment & Scraping
                        )
                    elif "Vectorizer" in log:
                        add_log("Vectorizer", log)
                        st.session_state.progress_stage = 3  # Vectorize
                    elif "Analyst" in log:
                        add_log("Analyst", log)
                        st.session_state.progress_stage = 4  # Analyze
                        st.session_state.agent_status["analyst"] = "running"
                        if "complete" in log.lower() or "finished" in log.lower():
                            st.session_state.agent_status["analyst"] = "success"
                    elif "Scraper" in log or "Scraping" in log:
                        add_log("Harvester", log)
                        # Specific matches for parallel UI tracks
                        if "Wikipedia" in log:
                            st.session_state.agent_status["wikipedia_agent"] = "success"
                        if "Yahoo" in log:
                            st.session_state.agent_status["yahoo_agent"] = "success"
                        if "ADX" in log:
                            st.session_state.agent_status["scraper"] = "success"
                        if "DFM" in log:
                            st.session_state.agent_status["ded_agent"] = "success"
                    else:
                        add_log("System", log)

            # --- Synchronized UI Update ---
            update_pipeline_ui()
            update_resolved_ui()

    # 4. Handle Completion
    if not resume_mode:
        # Resolution Phase complete -> Pause and wait for user to 'Generate Profile'
        st.session_state.investigation_paused = True
        st.session_state.intermediate_state = final_state
        add_log(
            "System",
            f"Company Resolved: {st.session_state.canonical_name}. Ready for deep profiling.",
        )
        # FINAL SYNC FOR RESOLUTION
        update_pipeline_ui()
        update_resolved_ui()
    else:
        # Enrichment & Synthesis Complete -> Final Dashboard
        st.session_state.investigation_paused = False
        st.session_state.analysis_complete = True
        st.session_state.progress_stage = 5  # Complete

        # Update Data from PresentationAgent (full overwrite)
        # This is the "develop" logic for financial summary segment
        if final_state and "meta" in final_state and "financials" in final_state:
            st.session_state.data = final_state
            st.session_state.agent_status["analyst"] = "success"
            add_log(
                "System",
                f"Intelligence Hub: Analysis complete for {st.session_state.canonical_name}",
            )
        elif final_state.get("financial_data"):
            # Fallback for raw scraper outputs
            real_data = final_state["financial_data"]
            if "financials" in real_data:
                st.session_state.data["financials"] = real_data["financials"]
            if "insights" in final_state:
                st.session_state.data["insights"] = final_state["insights"]

        # status.update removed as UI disabled
        update_pipeline_ui()


# --- Sidebar ---
with st.sidebar:
    # 1. Live Agent Trace Button (Prominent & Top)
    st.markdown(
        """
        <div style='display: flex; justify-content: center; width: 100%; margin-bottom: 24px; margin-top: 10px;'>
            <a href='https://smith.langchain.com/o/161479c6-ccc7-4a79-ab5b-8142f6f7ffa0/projects/p/c3f23a4a-4ff5-4202-b429-75fcc1fc0bff?timeModel=%7B%22duration%22%3A%227d%22%7D' target='_blank' style='
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                width: 100%;
                padding: 14px 20px;
                background: linear-gradient(135deg, #0077ff 0%, #00509e 100%);
                color: white;
                border: none;
                border-radius: 10px;
                text-decoration: none;
                font-family: "Poppins", sans-serif;
                font-weight: 700;
                font-size: 16px;
                letter-spacing: 0.03em;
                box-shadow: 0 4px 15px rgba(0, 80, 158, 0.3);
                transition: all 0.3s ease;
                text-transform: uppercase;
            ' onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 20px rgba(0, 80, 158, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0, 80, 158, 0.3)'">
                <span style='font-size: 18px;'>📡</span> Live Agent Trace
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- System Summary (Moved to Top) ---
    st.markdown(
        '<div class="sidebar-heading">📊 System Info</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"System Status: **ONLINE**")
    st.caption(f"Vector DB: **ChromaDB**")

    # Resolve LLM Provider name for display
    current_model_val = st.session_state.get("llm_model_select", LLMModel.GPT_4O.value)
    llm_provider = "Google" if "gemini" in current_model_val.lower() else "OpenAI"
    st.caption(f"LLM Provider: **{llm_provider}**")

    st.markdown("---")

    # --- Model Configuration ---
    st.markdown(
        '<div class="sidebar-heading">🛠️ Model Configuration</div>',
        unsafe_allow_html=True,
    )

    # Model Selector
    st.selectbox(
        "LLM Model",
        [model.value for model in LLMModel],
        index=[model.value for model in LLMModel].index(LLMModel.GPT_4O.value),
        format_func=lambda x: x.replace("models/", ""),
        key="llm_model_select",
        help="Select the underlying Large Language Model for agents.",
    )

    # Parameters
    st.slider(
        "Creativity Level",
        0.0,
        1.0,
        0.0,
        0.1,
        key="llm_temperature",
        help="Higher = More creative; Lower = More precise.",
    )
    st.slider(
        "Idea Diversity",
        0.0,
        1.0,
        1.0,
        0.05,
        key="llm_top_p",
        help="Higher = Diverse ideas; Lower = Most predictable result.",
    )
    st.slider(
        "Repitition Control",
        0.0,
        2.0,
        0.0,
        0.1,
        key="llm_freq_penalty",
        help="Higher = Reduces repetitive phrasing; Lower = Standard output.",
    )

    st.markdown("---")

    # --- Logs ---
    st.markdown(
        '<div class="sidebar-heading">📜 Live System Activity</div>',
        unsafe_allow_html=True,
    )
    log_container = st.empty()
    sidebar_logs_placeholder = log_container

    # Initial Render
    log_html_buffer = []
    for log in reversed(st.session_state.logs):
        # Parse simple prefix for better styling if present
        message = log
        prefix_elem = ""
        if ": " in log:
            parts = log.split(": ", 1)
            # Highlight the component name
            prefix_elem = f'<span class="log-prefix">{parts[0]}</span>'
            message = parts[1]

        log_html_buffer.append(
            f'<div class="log-entry">{prefix_elem}<span class="log-content">{message}</span></div>'
        )

    sidebar_logs_placeholder.markdown(
        f'<div class="log-scroller">{"".join(log_html_buffer)}</div>',
        unsafe_allow_html=True,
    )

    # Chatbot moved to right-side popover panel


# Banner with styled heading and tagline (matching reference)
st.markdown(
    f"""
    <div class="main-banner">
        <div style="display: flex; align-items: center; gap: 15px;">
            <img src="data:image/x-icon;base64,{logo_base64}" style="width: 50px; height: 50px; border-radius: 8px;">
            <div>
                <h1 class="main-heading" style="margin: 0;">CorporateIntelligenceX</h1>
                <p class="main-tagline" style="margin: 0; margin-top: 4px;">A smart GenAI-powered corporate information profiler.</p>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Feature tiles below banner
st.markdown(
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
    """,
    unsafe_allow_html=True,
)

# Search Company Label - professional styling
st.markdown(
    '<div class="ui-section-label"><span class="emoji">🔍</span><span>Search Company</span></div>',
    unsafe_allow_html=True,
)

# Input and Buttons in single row
cols = st.columns([5, 1, 1])

with cols[0]:
    query_input = st.text_input(
        "company_input",
        placeholder="Enter company name (e.g., Tesla, Emirates NBD, ADNOC)",
        label_visibility="collapsed",
        key=f"company_search_input_{st.session_state.reset_counter}",
    )

with cols[1]:
    search_clicked = st.button(
        "SEARCH", type="primary", width="stretch", icon=":material/search:"
    )

with cols[2]:
    reset_clicked = st.button(
        "RESET", type="secondary", width="stretch", icon=":material/refresh:"
    )

# Render Progress Chain (Always visible)
pipeline_placeholder = st.empty()
with pipeline_placeholder.container():
    # Use new pipeline visualization
    data = st.session_state.get("data", {})
    render_agent_pipeline(data, show_details=False)

# Canonical Name Section - professional styling
st.html('<div class="ui-section-label"></div>')

# Canonical Name Display
# Canonical Name Display
resolved_placeholder = st.empty()
continue_clicked = False

# Only render if NOT starting a new search (avoid duplicate key with run_investigation final state)
if not search_clicked:
    continue_clicked = render_company_summary_card(resolved_placeholder)

# Main Dashboard Placeholder
dashboard_placeholder = st.empty()

# Action: Continue Profiling
if continue_clicked:
    # Disable button immediately and show loading state
    st.session_state.is_generating = True
    st.session_state.investigation_paused = False
    # Show blinking dashboard placeholder before enrichment starts
    with dashboard_placeholder.container():
        company = st.session_state.get("canonical_name", "Company")
        _agents = [
            "Wikipedia Agent", "News Agent", "DED Agent",
            "Financial Scraper", "Analyst Agent"
        ]
        _agent_pills = "".join([
            f'<div style="display:flex;align-items:center;gap:10px;color:rgba(255,255,255,0.8);font-size:0.9rem;font-family:\'Inter\', sans-serif;font-weight:500;">'
            f'<span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
            f'background:#0077ff;box-shadow: 0 0 10px rgba(0, 119, 255, 0.5);animation:dashPulse 2s ease-in-out infinite;'
            f'animation-delay:{i * 0.3:.1f}s;"></span>{a}</div>'
            for i, a in enumerate(_agents)
        ])
        st.html(f"""
        <div style="
            margin-top: 32px;
            padding: 56px 40px;
            background: linear-gradient(135deg, #002D62 0%, #001A38 100%);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 45, 98, 0.25);
            animation: dashPulse 2.5s ease-in-out infinite;
        ">
            <style>
            @keyframes dashPulse {{
                0%, 100% {{ opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 rgba(0,119,255,0.0); }}
                50% {{ opacity: 0.9; transform: scale(0.99); box-shadow: 0 0 40px 6px rgba(0,119,255,0.25); }}
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            </style>
            <div style="
                width: 60px; height: 60px;
                border: 5px solid rgba(255,255,255,0.1);
                border-top-color: #0077ff;
                border-radius: 50%;
                animation: spin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite;
                margin: 0 auto 28px;
                box-shadow: 0 0 20px rgba(0, 119, 255, 0.2);
            "></div>
            <h3 style="
                color:#FFFFFF; 
                font-family: 'Poppins', sans-serif;
                font-size: 1.6rem; 
                font-weight: 700; 
                margin:0 0 12px;
                letter-spacing: -0.02em;
            ">Generating Intelligence Profile</h3>
            <p style="
                color:rgba(255,255,255,0.7); 
                font-family: 'Inter', sans-serif;
                font-size: 1.1rem; 
                margin:0 0 32px;
                line-height: 1.5;
            ">
                Running multi-agent enrichment for <strong style='color:#0077ff; font-weight: 700;'>{company}</strong>
            </p>
            <div style="display:flex; justify-content:center; gap:28px 40px; flex-wrap:wrap; max-width: 800px; margin: 0 auto;">
                {_agent_pills}
            </div>
        </div>
        """)
    run_investigation(
        None,
        pipeline_placeholder,
        resolved_placeholder,
        sidebar_logs_placeholder,
        dashboard_placeholder,
    )
    st.session_state.is_generating = False
    st.rerun()

if reset_clicked:
    # Set abort flag FIRST to stop ongoing workflow
    st.session_state.abort_investigation = True

    # COMPREHENSIVE STATE CLEAR
    keys_to_reset = [
        "data",
        "logs",
        "progress_stage",
        "analysis_complete",
        "canonical_name",
        "company_profile",
        "confidence_score",
        "is_resolving",
        "investigation_paused",
        "intermediate_state",
        "abort_investigation",
    ]

    for key in keys_to_reset:
        st.session_state[key] = (
            None
            if key != "logs"
            and key != "progress_stage"
            and key != "analysis_complete"
            and key != "is_resolving"
            and key != "investigation_paused"
            and key != "abort_investigation"
            else ([] if key == "logs" else (0 if key == "progress_stage" else False))
        )

    st.session_state.agent_status = get_default_agent_status()

    # INCREMENT COUNTER TO CLEAR WIDGET
    st.session_state.reset_counter += 1

    # Add log message
    add_log("System", "Dashboard fully reset")

    st.rerun()


# Trigger Search
if search_clicked and query_input:
    st.session_state.progress_stage = 1
    st.session_state.investigation_paused = False

    # Force UI update for instant feedback
    with pipeline_placeholder.container():
        # Use new pipeline visualization
        data = st.session_state.get("data", {})
        render_agent_pipeline(data, show_details=False)

    # Run investigation immediately (progress updates will stream)
    run_investigation(
        query_input,
        pipeline_placeholder,
        resolved_placeholder,
        sidebar_logs_placeholder,
        dashboard_placeholder,
    )
    st.rerun()

elif (
    query_input and not st.session_state.analysis_complete
):  # Allow Enter key if simple
    # logic to handle enter key is tricky with text_input without form,
    # but sidebar search button is explicit.
    # Let's rely on the button for the "Deep Search" feel requested.
    pass


# Final Dashboard Render (if analysis complete and not running investigation right now)
if st.session_state.analysis_complete and st.session_state.data:
    st.session_state.is_generating = False
    render_main_dashboard(dashboard_placeholder)

elif st.session_state.get("is_generating"):
    # Show blinking state while enrichment is actively running
    pass  # placeholder is already populated by the continue_clicked block above

elif not st.session_state.analysis_complete and st.session_state.progress_stage == 0:
    # Empty State - Show nothing or a welcome message
    pass


# ── IntelX Assistant (Right-side Popover) ──
_ix_ticker = st.session_state.get("ticker", "") or ""
if not _ix_ticker:
    _ix_data = st.session_state.get("data") or {}
    _ix_ticker = (_ix_data.get("company_profile") or {}).get("ticker", "") or ""
_ix_company = st.session_state.get("canonical_name", "") or ""

with st.popover("\U0001f4ac IntelX Assistant", width="content"):
    render_chatbot_panel(_ix_ticker, _ix_company)
