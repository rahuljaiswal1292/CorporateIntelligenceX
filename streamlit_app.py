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
)

image_path = os.path.join(
    os.path.dirname(__file__), "intelligence_hub", "ui", "favicon.jpg"
)


# --- Helper for Local Images (Base64) ---
def get_image_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


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
    initial_sidebar_state="expanded",
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


# --- Helper to append logs ---
def add_log(agent_name, action):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] **{agent_name}**: {action}"
    st.session_state.logs.append(log_entry)


# Helper to render the resolved name section
def render_resolved_ui(
    placeholder=None, key="btn_continue_investigation", show_button=True
):
    # Use placeholder if provided, else main flow
    context = placeholder.container() if placeholder else st.container()

    # Check if we should return early (user clicked Abort)
    if st.session_state.get("abort_investigation", False):
        return False

    with context:
        # Layout: Name Display | Continue Button
        # Use simple columns to keep Button aligned with Name at the top
        # Layout: Name Display (Full Width)
        # Use container for cleaner layout
        col_display = st.container()

        with col_display:
            if st.session_state.is_resolving and not st.session_state.canonical_name:
                # Resolving state
                st.html(
                    textwrap.dedent(
                        """
                    <div class="canonical-container" style="margin: 0;">
                        <div class="canonical-label">
                            <span class="canonical-icon">🏢</span>
                            <span class="canonical-title">RESOLVED COMPANY NAME</span>
                        </div>
                        <div class="canonical-value resolving">
                            <span class="canonical-text">Resolving...</span>
                        </div>
                    </div>
                    """
                    )
                )
            elif st.session_state.canonical_name:
                # Resolved state
                check = (
                    '<span class="canonical-check">✓</span>'
                    if st.session_state.canonical_name
                    else ""
                )
                status_class = "resolved"

                st.html(
                    textwrap.dedent(
                        f"""
                    <div class="canonical-container" style="margin: 0;">
                        <div class="canonical-label">
                            <span class="canonical-icon">🏢</span>
                            <span class="canonical-title">RESOLVED COMPANY NAME</span>
                        </div>
                        <div class="canonical-value {status_class}">
                            <span class="canonical-text">{st.session_state.canonical_name}</span>
                            {check}
                        </div>
                    </div>
                    """
                    )
                )
            else:
                # Default state
                st.markdown(
                    textwrap.dedent(
                        """
                    <div class="canonical-container" style="margin: 0;">
                        <div class="canonical-label">
                            <span class="canonical-icon">🏢</span>
                            <span class="canonical-title">RESOLVED COMPANY NAME</span>
                        </div>
                        <div class="canonical-value">
                            <span class="canonical-text">Ready to search</span>
                        </div>
                    </div>
                    """
                    ),
                    unsafe_allow_html=True,
                )

        # (Button moved to bottom)

        # Prepare Profile Data (Default: Not Available)
        desc = "No company profile data available yet. Start a search to generate insights."
        ticker_display = ""
        reason_text = "No data available"
        stakeholders_html = ""
        insights_html = '<div class="insight-item" style="color:#888;">No insights generated yet</div>'
        social_html = '<span style="color:#888; font-size:0.9rem;">Not Available</span>'
        badge_html = ""  # Hide badge by default
        kg_html = ""  # Hide KG by default
        show_stakeholders = False
        website_html = ""  # Hide website by default
        qa_html = ""  # Hide Q&A by default
        ref_html = ""  # Default empty

        # Override with real data if profile exists
        if st.session_state.canonical_name and st.session_state.company_profile:
            profile = st.session_state.company_profile

            # Safe extraction with defaults
            desc = profile.get("description", "No description available.")
            ticker = profile.get("ticker", "N/A")
            exchange = profile.get("exchange", "")
            ticker_display = (
                f"{exchange}:{ticker}" if exchange else (ticker if ticker else "")
            )

            # Confidence Logic
            confidence = profile.get("confidence_score", 0)
            conf_class = "medium"
            if confidence >= 90:
                conf_class = ""  # default green
            elif confidence < 50:
                conf_class = "low"

            badge_html = f"""
            <div class="confidence-badge {conf_class}">
                <span>{confidence}% Confidence</span>
            </div>
            """

            # Construct reasoning based on available data signals
            signals = profile.get("data_quality_signals", {})
            reasons = []
            if signals.get("knowledge_panel"):
                reasons.append("Knowledge Panel Verified")
            if signals.get("official_website"):
                reasons.append("Official Website")
            if signals.get("wikipedia_presence"):
                reasons.append("Wikipedia")
            reason_text = " • ".join(reasons) if reasons else "Based on search results"

            # Website extraction
            raw_url = (
                profile.get("website")
                or profile.get("official_website")
                or profile.get("url")
            )

            # Validate URL
            website_url = None
            if isinstance(raw_url, str) and raw_url.strip().startswith("http"):
                website_url = raw_url.strip()

            # Fallback to KG
            if not website_url:
                kg_tmp = profile.get("knowledge_graph", {})
                if isinstance(kg_tmp, dict):
                    val = kg_tmp.get("website")
                    if isinstance(val, str) and val.startswith("http"):
                        website_url = val

            # Fallback to First Organic Result
            if not website_url:
                organic = profile.get("organic_results", [])
                if organic and isinstance(organic, list) and len(organic) > 0:
                    val = organic[0].get("link")
                    if isinstance(val, str) and val.startswith("http"):
                        website_url = val

            website_html = ""
            if website_url:
                display_url = (
                    website_url.replace("https://", "")
                    .replace("http://", "")
                    .rstrip("/")
                )
                website_html = f"""
                <div style="margin-bottom: 20px; font-size: 0.9rem;">
                    <a href="{website_url}" target="_blank" style="text-decoration: none; color: #0066cc; font-weight: 500; display: inline-flex; align-items: center; gap: 6px;">
                        🔗 {display_url}
                    </a>
                </div>
                """

            # Knowledge Graph Extraction (Google Style)
            # Check nested object first (per new prompt), then fallback to specific fields
            kg_source = profile.get("knowledge_graph", {})
            if not isinstance(kg_source, dict):
                kg_source = {}

            kg_data = {}

            # 1. Customer Service (High priority in Google Panel)
            if kg_source.get("customer_service"):
                kg_data["Customer service"] = kg_source.get("customer_service")

            # 2. Leadership (CEO, Founder) - Try KG first, then generic profile
            ceo = kg_source.get("ceo")
            founder = kg_source.get("founder")

            # Fallback to leadership list/dict if not in KG dict
            leadership_data = profile.get("leadership", [])

            # Helper to check leadership fields in list or dict
            if not ceo:
                if isinstance(leadership_data, dict):
                    # Try keys like "CEO", "Chief Executive Officer"
                    for k, v in leadership_data.items():
                        if "ceo" in k.lower() or "chief executive" in k.lower():
                            ceo = v
                            break
                        if "ceo" in str(v).lower():
                            ceo = v  # In case value is "CEO: Name"
                            break
                elif isinstance(leadership_data, list):
                    for person in leadership_data:
                        p_name = (
                            person
                            if isinstance(person, str)
                            else person.get("name", "")
                        )
                        if (
                            "ceo" in p_name.lower()
                            or "chief executive" in p_name.lower()
                        ):
                            ceo = p_name
                            break

            if not founder:
                if isinstance(leadership_data, dict):
                    # Try keys like "Founder", "Co-Founder"
                    for k, v in leadership_data.items():
                        if "founder" in k.lower():
                            founder = v
                            break
                elif isinstance(leadership_data, list):
                    for person in leadership_data:
                        p_name = (
                            person
                            if isinstance(person, str)
                            else person.get("name", "")
                        )
                        if "founder" in p_name.lower():
                            founder = p_name
                            break

            if ceo:
                kg_data["CEO"] = ceo
            if founder:
                kg_data["Founder"] = founder

            # 3. Other Core Fields
            if kg_source.get("founded"):
                kg_data["Founded"] = kg_source.get("founded")
            if kg_source.get("headquarters"):
                kg_data["Headquarters"] = kg_source.get("headquarters")
            if kg_source.get("hubs"):
                kg_data["Hubs"] = kg_source.get("hubs")
            if kg_source.get("parent_organization"):
                kg_data["Parent Org"] = kg_source.get("parent_organization")

            # Check for fallbacks
            if "Founded" not in kg_data and profile.get("founded"):
                kg_data["Founded"] = profile.get("founded")
            if "Headquarters" not in kg_data and profile.get("headquarters"):
                kg_data["Headquarters"] = profile.get("headquarters")
            if "Type" not in kg_data and (kg_source.get("type") or profile.get("type")):
                kg_data["Type"] = kg_source.get("type") or profile.get("type")

            # 4. Industry/Sector & Stock
            industry = profile.get("industry") or profile.get("sector")
            if industry:
                kg_data["Industry"] = industry

            ticker = profile.get("ticker")
            exchange = profile.get("exchange")
            if ticker and ticker != "N/A":
                kg_data["Stock"] = f"{exchange}:{ticker}" if exchange else ticker

            # Subsidiaries
            subs = kg_source.get("subsidiaries") or profile.get("subsidiaries")
            if subs:
                if isinstance(subs, list):
                    kg_data["Subsidiaries"] = ", ".join([str(s) for s in subs[:3]]) + (
                        "..." if len(subs) > 3 else ""
                    )
                else:
                    kg_data["Subsidiaries"] = str(subs)

            # Dynamic Facts from LLM 'other_facts' or raw keys
            other_facts = kg_source.get("other_facts", {})
            if isinstance(other_facts, dict):
                for k, v in other_facts.items():
                    if k not in kg_data and v:
                        # Clean key (e.g. "net_income" -> "Net Income")
                        display_k = k.replace("_", " ").title()
                        # Clean value (if list)
                        if isinstance(v, list):
                            v = ", ".join([str(i) for i in v[:3]])
                        kg_data[display_k] = v

            # Fallback: Check top-level keys in kg_source we missed
            ignore_keys = {
                "title",
                "description",
                "source",
                "links",
                "kgmid",
                "type",
                "founded",
                "headquarters",
                "subsidiaries",
                "hubs",
                "parent_organization",
                "other_facts",
                "founders",
                "ceo",
                "stock_price",
            }
            for k, v in kg_source.items():
                key_lower = k.lower()
                if key_lower not in ignore_keys and k not in kg_data and v:
                    if isinstance(v, (str, int, float)):
                        display_k = k.replace("_", " ").title()
                        kg_data[display_k] = v

            if kg_data:
                rows = []
                for k, v in kg_data.items():
                    # Google Style: Bold Key + Value (Inline)
                    rows.append(
                        f"""
                     <div style="margin-bottom: 5px; font-size: 0.9rem; line-height: 1.5; color: #202124;">
                        <span style="font-weight: 700; color: #202124;">{k}:</span>
                        <span style="color: #4d5156;">{v}</span>
                     </div>
                     """
                    )
                kg_html = f'<div style="margin-top: 15px; margin-bottom: 20px;">{"".join(rows)}</div>'

            # Stakeholders & Shareholders Logic
            leadership_names = []
            shareholders_names = []
            shareholders = profile.get("major_shareholders") or profile.get(
                "ownership_structure", {}
            ).get("major_shareholders", [])

            # Parse Leadership (List or Dict)
            if isinstance(leadership_data, list):
                leadership_names.extend(
                    [
                        p if isinstance(p, str) else p.get("name", str(p))
                        for p in leadership_data[:4]
                    ]
                )
            elif isinstance(leadership_data, dict):
                # Convert to list of keys to slice safely
                l_keys = list(leadership_data.keys())
                for k in l_keys[:4]:
                    v = leadership_data[k]
                    # If key is Role (CEO) and value is Name (Amit Jain), show Name
                    if k.lower() in ["ceo", "founder", "chairman", "president"]:
                        leadership_names.append(v)
                    else:
                        leadership_names.append(f"{v}")

            # Parse Shareholders (List or Dict)
            if isinstance(shareholders, list):
                shareholders_names.extend(
                    [
                        s if isinstance(s, str) else s.get("name", str(s))
                        for s in shareholders[:4]
                    ]
                )
            elif isinstance(shareholders, dict):
                s_keys = list(shareholders.keys())
                for k in s_keys[:4]:
                    v = shareholders[k]
                    # If key is Name (longer) and value is Role (shorter description)
                    if len(k) > len(str(v)):
                        shareholders_names.append(f"{k} ({v})")
                    else:
                        shareholders_names.append(f"{v} ({k})")

            # Build HTML
            parts = []
            if leadership_names:
                parts.append(
                    '<div style="margin-bottom:8px;"><strong style="color:#555;">Leadership:</strong></div>'
                )
                for name in leadership_names:
                    parts.append(
                        f'<div style="margin-bottom:4px; padding-left:10px; border-left:2px solid #ddd;">👤 {name}</div>'
                    )

            if shareholders_names:
                parts.append(
                    '<div style="margin-top:12px; margin-bottom:8px;"><strong style="color:#555;">Major Shareholders:</strong></div>'
                )
                for name in shareholders_names:
                    parts.append(
                        f'<div style="margin-bottom:4px; padding-left:10px; border-left:2px solid #ddd;">🏢 {name}</div>'
                    )

            if parts:
                show_stakeholders = True
                stakeholders_html = "".join(parts)

            # Common Questions (SERP Q&A)
            qa_list = profile.get("common_questions", [])
            if qa_list and isinstance(qa_list, list):
                qa_items = []
                for item in qa_list[:3]:
                    q = item.get("question", "")
                    a = item.get("answer", "") or item.get("snippet", "")
                    if q and a:
                        qa_items.append(
                            f'<div style="margin-bottom:8px;"><strong style="color:#555;">Q: {q}</strong><br><span style="color:#666; font-size:0.9rem;">{a}</span></div>'
                        )

                if qa_items:
                    qa_html = f"""
                    <div class="summary-section" style="margin-top:20px; border-top:1px solid #eee; padding-top:10px;">
                        <h4>Common Questions</h4>
                        <div>{"".join(qa_items)}</div>
                    </div>
                    """

            # Social Links
            social_html = ""
            socials = profile.get("social_media", {})
            if not isinstance(socials, dict):
                socials = {}
            socials = socials.copy()

            # Add Wikipedia to Socials
            wiki_url = profile.get("wikipedia") or profile.get("wikipedia_url")
            if not wiki_url:
                # Check KG source
                kg_tmp = profile.get("knowledge_graph", {})
                if isinstance(kg_tmp, dict):
                    src = kg_tmp.get("source", {})
                    if src.get("name") and "wikipedia" in str(src.get("name")).lower():
                        wiki_url = src.get("link")

            if wiki_url:
                socials["Wikipedia"] = wiki_url

            if socials:
                for platform, url in socials.items():
                    if not url:
                        continue
                    icon = "🌐"
                    p_lower = platform.lower()
                    if "linkedin" in p_lower:
                        icon = "in"
                    elif "twitter" in p_lower or "x.com" in p_lower:
                        icon = "𝕏"
                    elif "facebook" in p_lower:
                        icon = "f"
                    elif "instagram" in p_lower:
                        icon = "📸"
                    elif "youtube" in p_lower:
                        icon = "▶️"
                    elif "wikipedia" in p_lower:
                        icon = "W"

                    social_html += f'<a href="{url}" target="_blank" class="social-icon" title="{platform}" style="margin-right:12px; text-decoration:none; font-size:1.1rem; color:#555;">{icon}</a>'

            # References Logic
            refs = list(profile.get("references", []))

            # Incorporate Organic Results (SERP Links)
            organic = profile.get("organic_results", [])
            seen_urls = {r.get("url") or r.get("link") for r in refs}

            if organic and isinstance(organic, list):
                for res in organic[:5]:
                    link = res.get("link")
                    if link and link not in seen_urls:
                        # Attempt to extract a short source name
                        raw_source = res.get("source") or res.get("title", "Link")
                        # Simple heuristic: often "Title - Source" or just "Source"
                        source_name = raw_source
                        if " - " in source_name:
                            source_name = source_name.split(" - ")[-1]

                        refs.append({"source": source_name[:20], "url": link})
                        seen_urls.add(link)

            if not refs:
                # Fallback to KG Source
                kg = profile.get("knowledge_graph", {})
                src = kg.get("source", {})
                if isinstance(src, dict) and src.get("link"):
                    refs.append(
                        {
                            "source": src.get("name", "Source")[:20],
                            "url": src.get("link"),
                        }
                    )

            if refs:
                ref_html = f"""
                <div class="summary-section" style="margin-top:20px; border-top:1px solid #eee; padding-top:10px;">
                    <h4 style="margin-bottom:12px; font-size:1rem; color:#202124;">References</h4>
                    <div style="display:flex; flex-wrap:wrap; gap:10px;">
                        {"".join([f'<a href="{r["url"]}" target="_blank" class="ref-tag" style="padding:4px 12px; background:#f1f3f4; border-radius:16px; color:#1a73e8; text-decoration:none; font-size:0.85rem; border:1px solid #dadce0;">{r["source"]}</a>' for r in refs[:4]])}
                    </div>
                </div>
                """

        # --- Render the Card ---
        # We always render the card shell if we have a canonical name
        if st.session_state.canonical_name:
            card_html = f"""
            <div class="summary-card">
                <div class="summary-header">
                    <div style="flex:1; display:flex; align-items:center; gap:20px;">
                        <div>
                            <h2 style="margin:0; font-size:1.5rem; color:#202124;">{st.session_state.canonical_name}</h2>
                            <div style="color:#70757a; font-size:0.9rem; margin-top:4px;">{reason_text}</div>
                        </div>
                        {badge_html}
                    </div>
                </div>
                
                <div style="display:grid; grid-template-columns: 2fr 1fr; gap:30px; margin-top:15px;">
                    <div>
                        {website_html}
                        <div style="color:#4d5156; font-size:1rem; line-height:1.6; margin-bottom:15px;">
                            {desc}
                        </div>
                        {qa_html}
                        {ref_html}
                    </div>
                    <div style="border-left:1px solid #eee; padding-left:20px;">
                        {kg_html}
                        {stakeholders_html}
                        <div style="margin-top:20px;">
                            <div style="margin-bottom:12px;"><strong style="color:#555;">CONNECT</strong></div>
                            <div class="social-links" style="margin-top:0;">
                                {social_html}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
            st.html(card_html)

            # Continue/Abort Controls (Only show if paused)
            if (
                st.session_state.investigation_paused
                and not st.session_state.analysis_complete
                and show_button
            ):
                st.html('<div style="height:20px;"></div>')
                col_abort, col_continue = st.columns([1, 2.5])

                with col_abort:
                    if st.button(
                        "🛑 ABORT", key=f"{key}_abort", use_container_width=True
                    ):
                        st.session_state.abort_investigation = True
                        st.session_state.data = None
                        st.session_state.logs = []
                        st.session_state.progress_stage = 0
                        st.session_state.analysis_complete = False
                        st.session_state.canonical_name = None
                        st.session_state.confidence_score = None
                        st.session_state.is_resolving = False
                        st.session_state.investigation_paused = False
                        st.session_state.agent_status = get_default_agent_status()
                        st.rerun()

                with col_continue:
                    btn_disabled = not st.session_state.canonical_name
                    if st.button(
                        "CONTINUE PROFILING →",
                        key=key,
                        disabled=btn_disabled,
                        type="primary",
                        use_container_width=True,
                    ):
                        return True
        elif st.session_state.is_resolving:
            # Show a beautiful shimmer loading placeholder
            st.html(
                """
            <div class="summary-card" style="opacity: 0.7;">
                <div class="shimmer" style="height: 30px; width: 60%; margin-bottom: 20px;"></div>
                <div class="shimmer" style="height: 100px; width: 100%; margin-bottom: 20px;"></div>
                <div style="display: flex; gap: 20px;">
                    <div class="shimmer" style="height: 200px; flex: 2;"></div>
                    <div class="shimmer" style="height: 200px; flex: 1;"></div>
                </div>
            </div>
            """
            )

    return False


# Cache the Agent Graph to avoid re-initialization overhead (DB connections etc)
# Cache the Agent Graphs
@st.cache_resource
def get_cached_resolution_graph_v5():
    return create_resolution_graph()


@st.cache_resource
def get_cached_enrichment_graph_v5():
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
        render_resolved_ui(
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
        graph = get_cached_resolution_graph_v5()
        input_data = {"query": query, "logs": [], "llm_config": llm_config}
        processed_logs = set()
    else:
        graph = get_cached_enrichment_graph_v5()
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

    # Stream the Graph execution (Use default 'updates' mode to track node progress)
    # We use a config with thread_id for state persistence/sync
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    stream = graph.stream(input_data, config=config)
    final_state = input_data.copy()

    # Initial Pipeline Update
    update_pipeline_ui()
    update_resolved_ui()

    for event in stream:
        # Check if user requested abort
        if st.session_state.abort_investigation:
            st.warning("⚠️ Investigation aborted by user")
            # status.update removed
            return

        # Event corresponds to a node finishing (in 'updates' mode)
        for node, state_update in event.items():
            # Update Agent Status based on finished node
            node_to_agent = {
                "resolution": "master_agent",
                "profiling": "master_agent",
                "wikipedia": "wikipedia_agent",
                "news": "news_agent",
                "ded": "ded_agent",
                "scraper": "scraper",
                "vectorizer": "vectorizer",
                "pdf_agent": "pdf_agent",
                "analyst": "analyst",
                "presentation_agent": "analyst",  # Presentation marks analyst stage complete
            }
            agent_key = node_to_agent.get(node)
            if agent_key:
                st.session_state.agent_status[agent_key] = "success"

                # Progression sequence (set running for next)
                if node in ("wikipedia", "news", "ded"):
                    # Check if all parallel agents finished
                    parallel_done = all(
                        st.session_state.agent_status.get(k) in ("success", "error")
                        for k in ["wikipedia_agent", "news_agent", "ded_agent"]
                    )
                    if parallel_done:
                        st.session_state.agent_status["scraper"] = "running"
                elif node == "scraper":
                    st.session_state.agent_status["pdf_agent"] = "running"
                    st.session_state.progress_stage = 3  # Move to Financials
                elif node == "pdf_agent":
                    st.session_state.agent_status["vectorizer"] = "running"
                elif node == "vectorizer":
                    st.session_state.agent_status["analyst"] = "running"
                    st.session_state.progress_stage = 4  # Move to Analyst
                elif node == "analyst":
                    pass  # presentation_agent will finish it

            # Capture canonical name from update if present
            state_canonical = state_update.get("canonical_name") or state_update.get(
                "company_name"
            )
            if state_canonical and not st.session_state.canonical_name:
                st.session_state.canonical_name = state_canonical
                st.session_state.is_resolving = False
                st.session_state.progress_stage = 2
                update_resolved_ui()

            # Capture profile data for Summary Card (Phase 1)
            if node == "master_enrichment" and "enrichments" in state_update:
                st.session_state.company_profile = state_update["enrichments"]
                update_resolved_ui()

            # Check for logs
            current_logs = state_update.get("logs", [])
            for log in current_logs:
                if log not in processed_logs:
                    processed_logs.add(log)
                    add_log("System", log)

        # Periodic UI update for live feedback
        update_pipeline_ui()

    # After stream ends, get the ABSOLUTE FINAL state for consistency
    final_full_state = graph.get_state(config).values
    final_state = final_full_state

    # 4. Handle Completion
    # 4. Handle Completion
    if not resume_mode:
        # Resolution Complete -> Pause
        st.session_state.intermediate_state = final_state
        st.session_state.investigation_paused = True
        st.session_state.is_resolving = False

        # Name resolution check
        if final_state.get("canonical_name"):
            st.session_state.canonical_name = final_state["canonical_name"]
            st.session_state.agent_status["master_agent"] = "success"

        # Ensure profile is captured for Phase 1 Summary Card
        if final_state.get("enrichments"):
            st.session_state.company_profile = final_state["enrichments"]

        update_pipeline_ui()
        update_resolved_ui()
        st.toast(
            "Canonical Resolution Complete. Click 'Continue' to proceed.", icon="⏸️"
        )
    else:
        # Enrichment Complete -> Finish
        st.session_state.investigation_paused = False
        st.session_state.analysis_complete = True
        st.session_state.progress_stage = 5  # Complete

        # Update Data from PresentationAgent (full overwrite)
        if final_state and "meta" in final_state and "financials" in final_state:
            # Full replacement to ensure no mock data leaks from initial session state
            st.session_state.data = final_state
            st.session_state.agent_status["analyst"] = "success"
            add_log(
                "System",
                f"Intelligence Hub: Analysis complete for {st.session_state.canonical_name}",
            )
        elif final_state.get("financial_data"):
            # Fallback
            real_data = final_state["financial_data"]
            if "financials" in real_data:
                st.session_state.data["financials"] = real_data["financials"]
            if "insights" in final_state:
                st.session_state.data["insights"] = final_state["insights"]

        update_pipeline_ui()
        update_resolved_ui()


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
cols = st.columns([5, 1, 1, 1.2])

with cols[0]:
    query_input = st.text_input(
        "company_input",
        placeholder="Enter company name (e.g., Tesla, Emirates NBD, ADNOC)",
        label_visibility="collapsed",
        key="company_search_input",
    )

with cols[1]:
    search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

with cols[2]:
    abort_clicked = st.button("🛑 Abort", type="secondary", use_container_width=True)

with cols[3]:
    test_data_clicked = st.button(
        "📊 Test Dashboard", type="secondary", use_container_width=True
    )

# Canonical Name Section - professional styling
st.markdown('<div class="ui-section-label"></div>', unsafe_allow_html=True)

# Canonical Name Display
# Canonical Name Display
resolved_placeholder = st.empty()
continue_clicked = False

# Only render if NOT starting a new search (avoid duplicate key with run_investigation final state)
if not search_clicked:
    continue_clicked = render_resolved_ui(resolved_placeholder)

# Render Progress Chain (Always visible)
st.markdown(
    '<div class="ui-section-label"><span class="emoji">⚙️</span><span>STATUS TRACKER</span></div>',
    unsafe_allow_html=True,
)

pipeline_placeholder = st.empty()
with pipeline_placeholder.container():
    # Use new pipeline visualization
    data = st.session_state.get("data", {})
    render_agent_pipeline(data, show_details=False)

# Main Dashboard Placeholder
dashboard_placeholder = st.empty()

# Action: Continue Profiling
if continue_clicked:
    # Ensure invalid states are cleared
    st.session_state.investigation_paused = False
    run_investigation(
        None,
        pipeline_placeholder,
        resolved_placeholder,
        sidebar_logs_placeholder,
        dashboard_placeholder,
    )
    st.rerun()

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
    st.session_state.agent_status = get_default_agent_status()

    # Add log message
    add_log("System", "Investigation aborted by user")

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

# Handle Test Data Button
if test_data_clicked:
    # Load mock data for testing from dashboard module
    st.session_state.data = get_test_dashboard_data()
    st.session_state.canonical_name = "Emirates NBD Bank PJSC"
    st.session_state.analysis_complete = True
    st.session_state.progress_stage = 5
    # Set all agents to success for test visualization
    st.session_state.agent_status = {k: "success" for k in get_default_agent_status()}
    st.success("✅ Test data loaded! Scroll down to see the dashboard.")
    st.rerun()


# Final Dashboard Render (if analysis complete and not running investigation right now)
if st.session_state.analysis_complete and st.session_state.data:
    render_main_dashboard(dashboard_placeholder)

elif not st.session_state.analysis_complete and st.session_state.progress_stage == 0:
    # Empty State - Show nothing or a welcome message
    pass
# End of Streamlit App - Force Reload 1
