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
from intelligence_hub.ui.chat_ui import render_chatbot_panel


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


# --- Formatting Helpers ---
def format_val(val):
    if val is None:
        return "N/A"
    try:
        if isinstance(val, (int, float)):
            if val > 1_000_000_000:
                return f"AED {val/1_000_000_000:.1f}B"
            if val > 1_000_000:
                return f"AED {val/1_000_000:.1f}M"
            return f"AED {val:,.0f}"
        return str(val)
    except:
        return "N/A"


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
                check = '<span class="canonical-check">✓</span>'

                status_class = "resolved"

                st.html(
                    textwrap.dedent(
                        f"""
                    <div class="canonical-container">
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
                    <div class="canonical-container">
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
                # Define high-quality colorful icons (Reliable PNG stickers)
                icon_assets = {
                    "linkedin": "https://img.icons8.com/color/48/linkedin.png",
                    "twitter": "https://img.icons8.com/color/48/twitterx--v1.png",
                    "x.com": "https://img.icons8.com/color/48/twitterx--v1.png",
                    "facebook": "https://img.icons8.com/color/48/facebook-new.png",
                    "instagram": "https://img.icons8.com/color/48/instagram-new.png",
                    "youtube": "https://img.icons8.com/color/48/youtube-play.png",
                    "wikipedia": "https://img.icons8.com/color/48/wikipedia.png",
                }

                social_html = ""
                for platform, url in socials.items():
                    if not url:
                        continue
                    p_lower = platform.lower()

                    # Match asset
                    img_src = "https://img.icons8.com/color/48/globe--v1.png"  # Global fallback
                    for key, asset_url in icon_assets.items():
                        if key in p_lower:
                            img_src = asset_url
                            break

                    social_html += f"""
                    <a href="{url}" target="_blank" class="social-icon" title="{platform}" 
                       style="margin-right:12px; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; 
                              width:36px; height:36px; border-radius:50%; background:white; border:1px solid #f0f0f0; 
                              box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition:transform 0.2s ease;">
                        <img src="{img_src}" style="width:20px; height:20px;" />
                    </a>
                    """

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
                col_continue, col_abort = st.columns([2.5, 1])

                with col_continue:
                    btn_disabled = not st.session_state.canonical_name
                    if st.button(
                        "🚀 GENERATE PROFILE",
                        key=key,
                        disabled=btn_disabled,
                        type="primary",
                        use_container_width=True,
                    ):
                        return True

                with col_abort:
                    if st.button(
                        "✖ CANCEL", key=f"{key}_abort", use_container_width=True
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

    # Stream the Graph execution
    stream = graph.stream(input_data)
    final_state = {}

    # Initial Pipeline Update
    update_pipeline_ui()
    update_resolved_ui()  # Initial Blink

    for event in stream:
        # Check if user requested abort
        if st.session_state.abort_investigation:
            st.warning("⚠️ Investigation aborted by user")
            # status.update removed
            return

        # Event corresponds to a node finishing
        for node, state in event.items():
            final_state = state  # Keep updating final state

            # ---- Map LangGraph node to agent_status key ----
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
                "start_enrichment": None,  # passthrough node
            }
            agent_key = node_to_agent.get(node)
            if agent_key:
                # Check if this node had an error — only look at NEW logs from this event
                # (not all accumulated logs, which may contain unrelated 'error'/'failed' words)
                node_logs = state.get("logs", [])
                # Only flag error if the LAST log entry (the most recent) indicates failure
                last_log = node_logs[-1].lower() if node_logs else ""
                has_error = ("failed" in last_log and "error" in last_log) or (
                    "exception" in last_log
                )
                st.session_state.agent_status[agent_key] = (
                    "error" if has_error else "success"
                )

                # Set next sequential agents to "running"
                if agent_key == "master_agent" and not has_error:
                    # After master, resolution graph ends. Enrichment runs on resume.
                    pass
                elif node == "start_enrichment":
                    # Parallel Enrichment Phase: Start all tracks simultaneously (Visual)
                    st.session_state.agent_status["wikipedia_agent"] = "running"
                    st.session_state.agent_status["news_agent"] = "running"
                    st.session_state.agent_status["ded_agent"] = "running"
                    st.session_state.agent_status["scraper"] = (
                        "running"  # ADX/Exchange Scraper
                    )
                    st.session_state.agent_status["yahoo_agent"] = "running"
                    st.session_state.agent_status["pdf_agent"] = (
                        "running"  # DED Filings
                    )

                    # Smart Skip Handling: If Exchange is known, mark the other as "completed" immediately
                    exchange_val = str(state.get("exchange", "")).upper()
                    if exchange_val == "DFM":
                        # Emaar etc. are DFM. Mark ADX as completed immediately.
                        st.session_state.agent_status["scraper"] = "success"
                    elif exchange_val == "ADX":
                        # Mark DFM as completed if this is strictly ADX
                        st.session_state.agent_status["ded_agent"] = "success"

                elif node in ("wikipedia", "news", "ded", "scraper", "pdf_agent"):
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
                        # Yahoo is usually handled via ScraperOrchestrator
                        if node == "scraper":
                            st.session_state.agent_status["yahoo_agent"] = "success"

                elif node == "vectorizer":
                    st.session_state.agent_status["vectorizer"] = "success"
                elif node == "analyst":
                    st.session_state.agent_status["analyst"] = "success"
                    st.session_state.analysis_complete = True

                update_pipeline_ui()

            # Capture canonical name from state if available
            state_canonical = state.get("canonical_name") or state.get("company_name")

            # Capture full profile data if available
            if "data" in state and isinstance(state["data"], dict):
                st.session_state.company_profile = state["data"]
            elif "enrichments" in state and isinstance(state["enrichments"], dict):
                # Sometimes under enrichments key
                st.session_state.company_profile = state["enrichments"]
            elif node == "profiling" and isinstance(state, dict):
                # profilng node might return enrichments directly in the state
                if "enrichments" in state:
                    st.session_state.company_profile = state["enrichments"]

            # Ensure UI reflects key state changes (async population)
            update_resolved_ui()

            if state_canonical and not st.session_state.canonical_name:
                import re as _re

                # Strip any HTML tags that might come from state (e.g. </div> from profiler output)
                state_canonical = _re.sub(r"<[^>]+>", "", str(state_canonical)).strip()
                if state_canonical:
                    st.session_state.canonical_name = state_canonical
                # Capture confidence score if available
                if state.get("confidence") or state.get("confidence_score"):
                    confidence = state.get("confidence") or state.get(
                        "confidence_score"
                    )
                    st.session_state.confidence_score = (
                        round(confidence)
                        if isinstance(confidence, (int, float))
                        else None
                    )
                st.session_state.is_resolving = False

                # Mark Stage 1 as Complete (Green) immediately
                st.session_state.progress_stage = 2
                update_pipeline_ui()
                update_resolved_ui()  # Resolved Name + Dashboard Refresh!

            # Check for new logs
            current_logs = state.get("logs", [])
            for log in current_logs:
                if log not in processed_logs:
                    processed_logs.add(log)

                    # UI Logic for Logs and Progress
                    if "Resolved" in log or "Canonical Name" in log:
                        add_log("Resolver", log)
                        st.session_state.progress_stage = 1  # Canonical Resolution
                        update_pipeline_ui()
                        # st.write(f"✅ {log}") # Disabled

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
                                update_pipeline_ui()
                                update_resolved_ui()  # Resolved via log + Dashboard Refresh!
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
                                update_pipeline_ui()
                                update_resolved_ui()  # Resolved via log + Dashboard Refresh!
                    elif "SERP" in log or "Profiling" in log:
                        add_log("SERP Agent", log)
                        # Only set to 1 if we haven't advanced to later stages (Resolution Done = 2)
                        if st.session_state.progress_stage < 2:
                            st.session_state.progress_stage = 1  # Merged with Canonical
                        update_pipeline_ui()
                        # st.write(f"🔍 {log}") # Disabled
                    elif "Enrichment" in log or "Scraping" in log:
                        add_log("Harvester", log)
                        st.session_state.progress_stage = (
                            2  # Parallel Enrichment & Scraping
                        )
                        update_pipeline_ui()
                        # st.write(f"⚡ {log}") # Disabled
                    elif "Vectorizer" in log:
                        add_log("Vectorizer", log)
                        st.session_state.progress_stage = 3  # Vectorize
                        update_pipeline_ui()
                        # st.write(f"🧠 {log}") # Disabled
                    elif "Analyst" in log:
                        add_log("Analyst", log)
                        st.session_state.progress_stage = 4  # Analyze
                        st.session_state.agent_status["analyst"] = "running"
                        if "complete" in log.lower() or "finished" in log.lower():
                            st.session_state.agent_status["analyst"] = "success"
                        update_pipeline_ui()
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
                        update_pipeline_ui()
                    else:
                        add_log("System", log)

    # 4. Handle Completion
    if not resume_mode:
        # Resolution Complete -> Pause
        st.session_state.intermediate_state = final_state
        st.session_state.investigation_paused = True
        st.session_state.is_resolving = False
        update_pipeline_ui()
        st.toast(
            "Canonical Resolution Complete. Click 'Continue' to proceed.", icon="⏸️"
        )
        # status.update removed
    else:
        # Enrichment Complete -> Finish
        st.session_state.investigation_paused = False
        st.session_state.analysis_complete = True

        # Update Data with Real Intelligence (Using final state)
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

                current_fin = {
                    "rev": format_val(real_fin.get("revenue")),
                    "profit": format_val(real_fin.get("net_income")),
                    "period": "LTM",  # Default to LTM for scraped data
                    "trend": None,  # clear mock trend
                    "price": (
                        format_val(real_fin.get("price"))
                        if "price" in real_fin
                        else "N/A"
                    ),
                }

                # Add Daily Summary if available (from Analyst)
                if "daily_summary" in real_data:
                    # Storing it for potential future use or display
                    current_fin["daily_summary"] = real_data["daily_summary"]

                # OVERWRITE with Real Data
                st.session_state.data["financials"] = {
                    "current": current_fin,
                    "last_year": {},  # Clear mock history
                    "last_quarter": {},  # Clear mock history
                }

                # Clear Mock Chart (since we don't have real chart data yet)
                st.session_state.data["chart"] = {}

            # 2. Update Profile (Overwrite Mock)
            if "profile" in real_data and real_data["profile"]:
                prof = real_data["profile"]
                # Ensure we don't lose the structure if we overwrite,
                # but we want to replace mock content.
                # Initialize properly if overwriting
                st.session_state.data["profile"] = {
                    "description": prof.get("description", "No description available."),
                    "sector": prof.get("sector", "Unknown Sector"),
                    "website": prof.get("website", ""),
                    # Keep other keys like 'est_date' from mock?
                    # User said "agent state should be considered".
                    # If agent didn't find est_date, we probably shouldn't show a fake one.
                    "est_date": prof.get("est_date", "N/A"),
                    "shareholders": prof.get("shareholders", []),
                }

                # If we have enrichment data for shareholders/exchange, map it?
                # PresentationAgent puts it in profile?
                # PresentationAgent implementation:
                # if enrichments.get("description"): final...["profile"]["description"] = ...
                # It doesn't seem to map shareholders explicitly in PresentationAgent.
                # We stick to what's in real_data["profile"].

            # 3. Update Sources
            if "sources" in real_data:
                st.session_state.data["sources"] = real_data["sources"]

        # C. Insights
        if final_state.get("insights"):
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

# Render Progress Chain (Always visible)
pipeline_placeholder = st.empty()
with pipeline_placeholder.container():
    # Use new pipeline visualization
    data = st.session_state.get("data", {})
    render_agent_pipeline(data, show_details=False)

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
        key=f"company_search_input_{st.session_state.reset_counter}",
    )

with cols[3]:
    test_data_clicked = st.button(
        "📊 Test Dashboard", type="secondary", use_container_width=True
    )

with cols[1]:
    search_clicked = st.button(
        "SEARCH", type="primary", use_container_width=True, icon=":material/search:"
    )

with cols[2]:
    reset_clicked = st.button(
        "RESET", type="secondary", use_container_width=True, icon=":material/refresh:"
    )


# Canonical Name Section - professional styling
st.html('<div class="ui-section-label"></div>')

# Canonical Name Display
# Canonical Name Display
resolved_placeholder = st.empty()
continue_clicked = False

# Only render if NOT starting a new search (avoid duplicate key with run_investigation final state)
if not search_clicked:
    continue_clicked = render_resolved_ui(resolved_placeholder)

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


# ── IntelX Assistant (Right-side Popover) ──
_ix_ticker = st.session_state.get("ticker", "") or ""
if not _ix_ticker:
    _ix_data = st.session_state.get("data") or {}
    _ix_ticker = (_ix_data.get("company_profile") or {}).get("ticker", "") or ""
_ix_company = st.session_state.get("canonical_name", "") or ""

with st.popover("\U0001f4ac IntelX Assistant", use_container_width=False):
    render_chatbot_panel(_ix_ticker, _ix_company)
