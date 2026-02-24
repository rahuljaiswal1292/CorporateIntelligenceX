import os
import time
import uuid
from pathlib import Path
from datetime import datetime
import streamlit as st
import json
from intelligence_hub.agents.chat_agent import ChatAgent
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.vector_manager import VectorManager

# ─────────────────────────────────────────────────────────────────────────────
# INTELX ASSISTANT  —  RIGHT PANEL EDITION (V3)
# Brand-aligned navy/gold professional styling
# ─────────────────────────────────────────────────────────────────────────────

_PANEL_CSS = """
<style>
/* ── IntelX Right Panel ── */
.ix-panel-header {
    display: none;
}
.ix-panel-icon {
    background: linear-gradient(135deg, #FFB600 0%, #FF9500 100%);
    width: 44px; height: 44px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; color: #FFFFFF;
    box-shadow: 0 4px 12px rgba(255, 182, 0, 0.4);
    font-size: 16px;
    flex-shrink: 0;
    font-family: 'Poppins', sans-serif;
}
.ix-panel-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
    color: #003366;
    letter-spacing: 0.02em;
    font-family: 'Poppins', sans-serif;
}
.ix-panel-subtitle {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    margin: 0;
    margin-top: 2px;
    letter-spacing: 1.5px;
    font-weight: 500;
    font-family: 'Poppins', sans-serif;
}

/* ── Status Badge ── */
.ix-panel-status {
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 10px;
    padding: 8px 14px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.85rem;
    color: #0369a1;
    font-weight: 600;
    transition: all 0.3s ease;
}
.ix-panel-status-waiting {
    background: #fffbeb;
    border: 1px solid #fef3c7;
    color: #b45309;
}
.ix-status-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    animation: ix-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
.ix-dot-green { background: #10b981; box-shadow: 0 0 8px rgba(16, 185, 129, 0.6); }
.ix-dot-amber { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.6); }
@keyframes ix-pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.9); } 100% { opacity: 1; transform: scale(1); } }

/* ── Quick Actions ── */
.ix-actions-label {
    font-size: 0.75rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 8px 0 8px 4px;
    font-weight: 700;
}

/* ── Welcome Message ── */
.ix-welcome {
    text-align: center;
    padding: 40px 20px;
    color: #64748b;
    border: 2px dashed #e2e8f0;
    border-radius: 20px;
    margin: 10px 0;
    background: #fdfeff;
}
.ix-welcome-wave {
    font-size: 3rem;
    margin-bottom: 15px;
    display: block;
    filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));
}
.ix-welcome-text {
    font-size: 0.9rem;
    line-height: 1.6;
    color: #64748b;
}

/* ── Chat bubbles ── */
.ix-chat-area [data-testid="stChatMessage"] {
    background: white !important;
    border-radius: 16px !important;
    border: 1px solid #f1f5f9 !important;
    margin-bottom: 12px !important;
    padding: 14px !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02) !important;
}
.ix-chat-area [data-testid="stChatMessage"] p {
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
    color: #1e293b !important;
}

/* ── Custom Scrollbar for Chat Area ── */
.ix-chat-area div[data-testid="stVerticalBlock"] {
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
    width: 100% !important;
}
.ix-chat-area div[data-testid="stVerticalBlock"]::-webkit-scrollbar {
    width: 8px;
}
/* Force columns in popover to respect the width */
[data-testid="stPopoverBody"] div[data-testid="stVerticalBlock"] {
    width: 100% !important;
}
.ix-chat-area div[data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
    background-color: #cbd5e1;
    border-radius: 20px;
}

/* ── Quick Action Button Overrides ── */
.ix-chat-area + div .stButton button {
    background: #f8fafc !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: none !important;
    padding: 8px 12px !important;
}
.ix-chat-area + div .stButton button:hover {
    background: #003366 !important;
    color: white !important;
    border-color: #003366 !important;
}

/* ── Custom Chat Avatars (SVG) ──── */
/* We'll use these in the code via base64 */
</style>
"""

# Professional SVG Avatars
_BOT_AVATAR_SVG = """
<svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="40" height="40" rx="20" fill="#003366"/>
    <text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" fill="#FFB600" font-family="Poppins, sans-serif" font-weight="800" font-size="14">IX</text>
</svg>
"""

_USER_AVATAR_SVG = """
<svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="40" height="40" rx="20" fill="#E2E8F0"/>
    <path d="M20 21C22.7614 21 25 18.7614 25 16C25 13.2386 22.7614 11 20 11C17.2386 11 15 13.2386 15 16C15 18.7614 17.2386 21 20 21Z" fill="#64748B"/>
    <path d="M20 23C16.134 23 13 26.134 13 30H27C27 26.134 23.866 23 20 23Z" fill="#64748B"/>
</svg>
"""

import base64


def _get_svg_base64(svg_str: str) -> str:
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_str.strip().encode()).decode()}"


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _PROJECT_ROOT / "data"


@st.cache_resource(show_spinner=False)
def _get_vector_manager() -> VectorManager:
    return VectorManager()


@st.cache_resource(show_spinner=False)
def _get_chat_agent(company_name: str) -> ChatAgent:
    return ChatAgent(
        company_name=company_name,
        llm_connector=LLMConnector(),
        vector_manager=_get_vector_manager(),
    )


def _ensure_vectors_ingested(ticker: str, vm: VectorManager):
    """Automatically ingest data from structured/md folders for the company."""
    if not ticker:
        return

    ticker_upper = ticker.upper()
    ingested_key = f"ix_ingested_{ticker_upper}"
    if st.session_state.get(ingested_key):
        return

    # Tracking for toast
    total_files = 0
    processed_paths = set()

    # Search strategy:
    # 1. data/EXCHANGE/TICKER/**/[md|structured]
    # 2. data/TICKER/**
    # 3. data/CANONICAL_NAME/**

    search_dirs = []
    if _DATA_ROOT.exists():
        # Option 1: Standard exchange/ticker structure
        for exchange_dir in _DATA_ROOT.iterdir():
            if not exchange_dir.is_dir():
                continue
            ticker_dir = exchange_dir / ticker_upper
            if ticker_dir.exists():
                search_dirs.append(ticker_dir)

        # Option 2: Direct ticker folder in root
        direct_dir = _DATA_ROOT / ticker_upper
        if direct_dir.exists() and direct_dir not in search_dirs:
            search_dirs.append(direct_dir)

        # Option 3: Lowercase or normalized names (e.g. emaar_properties_pjsc)
        canonical = st.session_state.get("canonical_name", "").lower().replace(" ", "_")
        if canonical:
            can_dir = _DATA_ROOT / canonical
            if can_dir.exists() and can_dir not in search_dirs:
                search_dirs.append(can_dir)

    for ticker_dir in search_dirs:
        # Use rglob to find all relevant files in the company directory
        # We index .md, .txt, and optionally extract from .json
        for f in ticker_dir.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in (".md", ".txt", ".json"):
                continue

            # Avoid re-processing same file if found via multiple search dirs
            if str(f) in processed_paths:
                continue
            processed_paths.add(str(f))

            try:
                content = ""
                if f.suffix.lower() == ".json":
                    with open(f, "r", encoding="utf-8", errors="ignore") as jf:
                        try:
                            data = json.load(jf)
                            # If it's a list, stringify it
                            if isinstance(data, (dict, list)):
                                content = json.dumps(data, indent=2)
                            else:
                                content = str(data)
                        except:
                            continue
                else:
                    content = f.read_text(encoding="utf-8", errors="ignore")

                if len(content.strip()) < 50:
                    continue

                chunks = vm.chunk_text(content)
                ids, docs, metas = [], [], []
                for i, chunk in enumerate(chunks):
                    # Unique ID per chunk
                    cid = f"{ticker_upper}_{f.stem}_{i}_{str(uuid.uuid4())[:6]}"
                    ids.append(cid)
                    docs.append(chunk)
                    metas.append(
                        {
                            "ticker": ticker_upper,
                            "source": f.name,
                            "path": str(f.relative_to(_PROJECT_ROOT)),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

                if ids:
                    vm.collection.add(ids=ids, documents=docs, metadatas=metas)
                    total_files += 1
            except Exception as e:
                # Silently fail for individual files but keep record
                pass

    st.session_state[ingested_key] = True
    if total_files > 0:
        st.toast(
            f"IntelX: Synced {total_files} documents for {ticker_upper}", icon="⚡"
        )
    else:
        # If we found no files, maybe don't mark as ingested so it can retry if more data arrives
        st.session_state[ingested_key] = False


def render_chatbot_panel(ticker: str, company_name: str):
    """
    Renders the IntelX Assistant as a right-side panel.
    """
    st.markdown(_PANEL_CSS, unsafe_allow_html=True)

    # 1. Initialize session state
    if "ix_messages" not in st.session_state:
        st.session_state.ix_messages = []
    if "ix_inject" not in st.session_state:
        st.session_state.ix_inject = None

    # Reset chat if company changes
    last_company = st.session_state.get("ix_last_company")
    if company_name and last_company != company_name:
        st.session_state.ix_messages = []
        st.session_state.ix_last_company = company_name
        # Add a friendly sync notification as the first message
        st.session_state.ix_messages.append(
            {
                "role": "assistant",
                "content": f"⚡ **IntelX Synced**: Intelligence Hub is now connected to **{company_name}**. How can I help you today?",
            }
        )

    # 2. Process Vector Ingestion if company is active
    if ticker and company_name:
        vm = _get_vector_manager()
        _ensure_vectors_ingested(ticker, vm)

    # 3. Define Callback to handle submission and clear input
    def on_chat_submit():
        user_input = st.session_state.get("ix_text_input_raw", "").strip()
        if user_input and company_name:
            st.session_state.ix_messages.append({"role": "user", "content": user_input})
            st.session_state["ix_pending_query"] = user_input
            # Clear the input widget
            st.session_state["ix_text_input_raw"] = ""

    # Check for injected quick questions
    if st.session_state.ix_inject:
        st.session_state.ix_messages.append(
            {"role": "user", "content": st.session_state.ix_inject}
        )
        st.session_state["ix_pending_query"] = st.session_state.ix_inject
        st.session_state.ix_inject = None

    # ── Status ──
    if company_name:
        st.markdown(
            f"""
        <div class="ix-panel-status">
            <div class="ix-status-dot ix-dot-green"></div>
            Synced: <b>{company_name}</b>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
        <div class="ix-panel-status ix-panel-status-waiting">
            <div class="ix-status-dot ix-dot-amber"></div>
            Awaiting company data...
        </div>
        """,
            unsafe_allow_html=True,
        )

    # ── Quick Actions ──
    if company_name:
        st.markdown(
            '<div class="ix-actions-label">💡 Quick Questions</div>',
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("📊 Revenue", key="ix_btn_rev", width="stretch"):
                st.session_state.ix_inject = (
                    f"What are the latest revenue trends for {company_name}?"
                )
        with c2:
            if st.button("💹 Stock", key="ix_btn_stock", width="stretch"):
                st.session_state.ix_inject = (
                    f"How is the stock performance for {company_name}?"
                )

        c3, c4 = st.columns(2, gap="small")
        with c3:
            if st.button("🏛️ Strategy", key="ix_btn_strat", width="stretch"):
                st.session_state.ix_inject = (
                    f"What is the strategic vision for {company_name}?"
                )
        with c4:
            if st.button("🗞️ News", key="ix_btn_news", width="stretch"):
                st.session_state.ix_inject = (
                    f"Summarize recent news for {company_name}."
                )

        # ── Knowledge Inventory ──
        # with st.expander("📂 Knowledge Base", expanded=False):
        #     if not ticker:
        #         st.caption("Search for a company to view the knowledge base.")
        #     else:
        #         vm = _get_vector_manager()
        #         try:
        #             results = vm.collection.get(
        #                 where={"ticker": ticker.upper()}, include=["metadatas"]
        #             )
        #             if results["metadatas"]:
        #                 sources = {
        #                     m.get("source", "Unknown") for m in results["metadatas"]
        #                 }
        #                 for src in sorted(list(sources)):
        #                     icon = (
        #                         "📄"
        #                         if src.endswith(".pdf")
        #                         else ("📊" if src.endswith(".csv") else "📝")
        #                     )
        #                     st.markdown(
        #                         f'<div class="ix-inventory-item">{icon} {src}</div>',
        #                         unsafe_allow_html=True,
        #                     )
        #                 st.markdown(
        #                     f'<div class="ix-inventory-count">Total Chunks: {len(results["metadatas"])}</div>',
        #                     unsafe_allow_html=True,
        #                 )
        #             else:
        #                 st.caption(f"No documents indexed yet for {ticker.upper()}.")
        #         except Exception as e:
        #             st.caption(f"Indexing in progress for {ticker.upper()}...")

    # ── Separator ──
    st.markdown("---")

    # ── Chat Area ──
    st.markdown('<div class="ix-chat-area">', unsafe_allow_html=True)
    chat_container = st.container(height=300)
    with chat_container:
        if not st.session_state.ix_messages:
            st.markdown(
                """
            <div class="ix-welcome">
                <span class="ix-welcome-wave">👋</span>
                <div class="ix-welcome-text">
                    Your strategic advisor for UAE Corporate Intelligence.<br>
                    I have analyzed financial reports, news, and market data.<br>
                    <b>How can I help you today?</b>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        bot_avatar = _get_svg_base64(_BOT_AVATAR_SVG)
        user_avatar = _get_svg_base64(_USER_AVATAR_SVG)

        for msg in st.session_state.ix_messages:
            avatar = bot_avatar if msg["role"] == "assistant" else user_avatar
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Input Area ──
    # We use a columns-based layout for input and send button
    input_col, send_col = st.columns([5, 1])
    with input_col:
        st.text_input(
            "Ask IntelX",
            placeholder="Ask IntelX Assistant...",
            key="ix_text_input_raw",
            label_visibility="collapsed",
            on_change=on_chat_submit,
        )
    with send_col:
        st.button(
            "➤",
            key="ix_send_btn",
            width="stretch",
            type="primary",
            on_click=on_chat_submit,
        )

    # ── Handle Logic for Pending Response ──
    pending_query = st.session_state.get("ix_pending_query")
    if pending_query and company_name:
        # Remove pending flag to prevent re-submission
        del st.session_state["ix_pending_query"]

        bot_avatar = _get_svg_base64(_BOT_AVATAR_SVG)

        with chat_container:
            # Re-render messages is handled high up, we just add the assistant one now
            with st.chat_message("assistant", avatar=bot_avatar):
                placeholder = st.empty()
                full_response = ""
                with st.spinner(""):
                    vm = _get_vector_manager()
                    agent = _get_chat_agent(company_name)

                    # LIMIT CONTEXT WINDOW: Last 10 messages (5 turns)
                    context_history = (
                        st.session_state.ix_messages[-10:-1]
                        if len(st.session_state.ix_messages) > 1
                        else []
                    )

                    response = agent.answer_query(
                        query=pending_query,
                        ticker=ticker,
                        history=context_history,
                    )

                # Streaming effect
                words = response.split()
                for i, word in enumerate(words):
                    full_response += word + " "
                    if i % 3 == 0:  # Update every 3 words for smoothness
                        placeholder.markdown(full_response + "▌")
                        time.sleep(0.01)
                placeholder.markdown(full_response.strip())

        st.session_state.ix_messages.append(
            {"role": "assistant", "content": full_response.strip()}
        )
        st.rerun()

    # ── Clear Button ──
    if st.session_state.ix_messages:
        if st.button(
            "🗑️ Reset Conversation",
            key="ix_clear",
            width="stretch",
            type="secondary",
        ):
            st.session_state.ix_messages = []
            st.rerun()
