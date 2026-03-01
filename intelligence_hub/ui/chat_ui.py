import os
import re
import time
import uuid
from pathlib import Path
from datetime import datetime
import streamlit as st
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
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding: 14px 16px;
    background: linear-gradient(135deg, #002D62 0%, #001A38 100%);
    border-radius: 12px;
    border: 1px solid rgba(0, 45, 98, 0.3);
}
.ix-panel-icon {
    background: linear-gradient(135deg, #FFB600 0%, #FF9500 100%);
    width: 38px; height: 38px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 900; color: #002D62;
    box-shadow: 0 4px 12px rgba(255, 182, 0, 0.3);
    font-size: 14px;
    flex-shrink: 0;
}
.ix-panel-title {
    font-size: 1rem;
    font-weight: 700;
    margin: 0;
    color: #FFFFFF;
    font-family: 'Poppins', 'Segoe UI', sans-serif;
}
.ix-panel-subtitle {
    font-size: 0.7rem;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    margin: 0;
    letter-spacing: 1px;
    font-family: 'Poppins', 'Segoe UI', sans-serif;
}

/* ── Status Badge ── */
.ix-panel-status {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 8px;
    padding: 8px 14px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.8rem;
    color: #166534;
    font-weight: 600;
}
.ix-panel-status-waiting {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    color: #92400E;
}
.ix-status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    animation: ix-pulse 2s infinite;
}
.ix-dot-green { background: #10b981; box-shadow: 0 0 6px #10b981; }
.ix-dot-amber { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }
@keyframes ix-pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }

/* ── Quick Actions ── */
.ix-actions-label {
    font-size: 0.7rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 10px;
    font-weight: 700;
    font-family: 'Poppins', 'Segoe UI', sans-serif;
}

/* ── Chat message styling ── */
.ix-welcome {
    text-align: center;
    padding: 30px 15px;
    color: #94A3B8;
    font-size: 0.85rem;
    border: 1px dashed #E2E8F0;
    border-radius: 12px;
    margin: 10px 0;
    background: #FAFBFD;
}
.ix-welcome-wave {
    font-size: 2.5rem;
    margin-bottom: 10px;
    display: block;
}
.ix-welcome-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #002D62;
    margin-bottom: 6px;
}

/* ── Knowledge Inventory ── */
.ix-inventory-item {
    font-size: 0.78rem;
    color: #475569;
    margin-bottom: 4px;
    padding: 4px 8px;
    background: #F8FAFC;
    border-radius: 6px;
    border: 1px solid #F1F5F9;
}
.ix-inventory-count {
    font-size: 0.7rem;
    color: #002D62;
    font-weight: 600;
    margin-top: 8px;
}

/* ── Override Streamlit chat styling in the right panel ── */
.ix-chat-area [data-testid="stChatMessage"] {
    background: #ffffff !important;
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    margin-bottom: 12px !important;
    padding: 12px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
}

/* Avatar Containers */
.ix-chat-area [data-testid="stChatMessageAvatarAssistant"] {
    background: #e0f2fe !important;
    color: #002D62 !important;
    border: 1px solid #bae6fd !important;
    box-shadow: 0 2px 6px rgba(0,45,98,0.1) !important;
}

.ix-chat-area [data-testid="stChatMessageAvatarUser"] {
    background: #ffffff !important;
    color: #475569 !important;
    border: 1px solid #e2e8f0 !important;
}

.ix-chat-area [data-testid="stChatMessage"] p {
    font-size: 0.95rem !important;
    line-height: 1.7 !important;
    color: #1E293B !important;
    font-family: 'Poppins', sans-serif !important;
    margin-bottom: 12px !important;
}

/* Ensure lists have proper indentation and spacing */
.ix-chat-area [data-testid="stChatMessage"] ul, 
.ix-chat-area [data-testid="stChatMessage"] ol {
    padding-left: 20px !important;
    margin-bottom: 15px !important;
}

.ix-chat-area [data-testid="stChatMessage"] li {
    font-size: 0.95rem !important;
    line-height: 1.6 !important;
    margin-bottom: 8px !important;
    color: #334155 !important;
}

/* Highlighted text in chat */
.ix-chat-area [data-testid="stChatMessage"] strong {
    color: #002D62 !important;
    font-weight: 700 !important;
}

/* ── Quick Actions Grid ── */
.ix-chat-area [data-testid="baseButton-secondary"] {
    text-align: left !important;
    height: auto !important;
    min-height: 54px !important;
    padding: 8px 12px !important;
    white-space: normal !important;
    line-height: 1.3 !important;
    font-size: 0.8rem !important;
    border: 1px solid #E2E8F0 !important;
    background: #FFFFFF !important;
    color: #475569 !important;
    align-items: flex-start !important;
    justify-content: flex-start !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    transition: all 0.2s ease !important;
}
.ix-chat-area [data-testid="baseButton-secondary"]:hover {
    border-color: #002D62 !important;
    background: #F8FAFC !important;
    color: #002D62 !important;
    box-shadow: 0 4px 6px rgba(0,45,98,0.05) !important;
}

</style>
"""

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
    ingested_key = f"ix_ingested_{ticker.upper()}"
    if st.session_state.get(ingested_key):
        return

    ticker_upper = ticker.upper()
    total_files = 0

    if _DATA_ROOT.exists():
        for exchange_dir in _DATA_ROOT.iterdir():
            if not exchange_dir.is_dir():
                continue
            ticker_dir = exchange_dir / ticker_upper
            if not ticker_dir.exists():
                continue

            for sub_type in ("md", "structured"):
                for source_dir in ticker_dir.rglob(sub_type):
                    if not source_dir.is_dir():
                        continue
                    for f in source_dir.iterdir():
                        if f.suffix.lower() in (".md", ".txt"):
                            try:
                                content = f.read_text(encoding="utf-8", errors="ignore")
                                if len(content.strip()) < 50:
                                    continue

                                chunks = vm.chunk_text(content)
                                ids, docs, metas = [], [], []
                                for i, chunk in enumerate(chunks):
                                    ids.append(
                                        f"{ticker_upper}_{f.stem}_{i}_{str(uuid.uuid4())[:6]}"
                                    )
                                    docs.append(chunk)
                                    metas.append(
                                        {
                                            "ticker": ticker_upper,
                                            "source": f.name,
                                            "timestamp": datetime.now().isoformat(),
                                        }
                                    )

                                if ids:
                                    vm.collection.add(
                                        ids=ids, documents=docs, metadatas=metas
                                    )
                                    total_files += 1
                            except Exception:
                                pass

    st.session_state[ingested_key] = True
    if total_files > 0:
        st.toast(
            f"IntelX: Synced {total_files} documents for {ticker_upper}", icon="⚡"
        )


def render_chatbot_panel(ticker: str, company_name: str):
    """
    Renders the IntelX Assistant as a right-side panel.
    This is called inside a column or container in the main app.
    Uses brand-aligned light theme (navy/gold) to match the main page.
    """
    st.markdown(_PANEL_CSS, unsafe_allow_html=True)

    if "ix_messages" not in st.session_state:
        st.session_state.ix_messages = []
    if "ix_inject" not in st.session_state:
        st.session_state.ix_inject = None

    # ── Header ──
    st.markdown(
        """
    <div class="ix-panel-header">
        <div class="ix-panel-icon">IX</div>
        <div>
            <div class="ix-panel-title">IntelX Assistant</div>
            <div class="ix-panel-subtitle">Strategic Advisor</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

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

        # Dynamic questions based on company (Actual questions, no icons)
        questions = [
            (
                "What are the latest revenue trends?",
                f"What are the latest revenue trends and financial performance for {company_name}?",
            ),
            (
                "What are the key risk factors?",
                f"What are the key risk factors and credit ratings for {company_name}?",
            ),
            (
                "What is the strategic vision?",
                f"What is the strategic vision and major masterplans for {company_name}?",
            ),
            (
                "Summarize recent project launches",
                f"Summarize the most recent news and project launches for {company_name}.",
            ),
        ]

        if "EMAAR" in (ticker or "").upper() or "EMAAR" in (company_name or "").upper():
            questions = [
                (
                    "Status of AED 2.5B Sukuk (Dec 2025)?",
                    f"Tell me about Emaar's AED 2.5B Sukuk maturity in December 2025.",
                ),
                (
                    "Details on 'The Heights' masterplan?",
                    f"What information is available regarding Emaar's new masterplan 'The Heights'?",
                ),
                (
                    "Revenue split for Egypt and India?",
                    f"How much of Emaar's revenue comes from international operations like Egypt and India?",
                ),
                (
                    "Q3 2024 Revenue & Profit growth?",
                    f"What was Emaar's revenue and profit growth in Q3 2024?",
                ),
            ]
        elif "ENBD" in (ticker or "").upper() or "NBD" in (company_name or "").upper():
            questions = [
                (
                    "Growth in Saudi Arabia assets?",
                    f"Tell me about Emirates NBD's 18% asset growth in Saudi Arabia.",
                ),
                (
                    "Digital impact on Cost-to-Income?",
                    f"How has digital adoption impacted Emirates NBD's cost-to-income ratio?",
                ),
                (
                    "Current Liquidity Coverage Ratio (LCR)?",
                    f"What is the current Liquidity Coverage Ratio (LCR) for Emirates NBD?",
                ),
                (
                    "FY 2024 Financial Results Summary",
                    f"Summarize the FY 2024 financial results for Emirates NBD.",
                ),
            ]

        # Render 2x2 grid (Questions now use full text labels)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(questions[0][0], key="ix_btn_1", use_container_width=True):
                st.session_state.ix_inject = questions[0][1]
            if st.button(questions[2][0], key="ix_btn_3", use_container_width=True):
                st.session_state.ix_inject = questions[2][1]
        with c2:
            if st.button(questions[1][0], key="ix_btn_2", use_container_width=True):
                st.session_state.ix_inject = questions[1][1]
            if st.button(questions[3][0], key="ix_btn_4", use_container_width=True):
                st.session_state.ix_inject = questions[3][1]

    # ── Separator ──
    st.markdown("---")

    # ── Chat Area ──
    st.markdown('<div class="ix-chat-area">', unsafe_allow_html=True)
    chat_container = st.container(height=350)
    with chat_container:
        if not st.session_state.ix_messages:
            st.markdown(
                """
            <div class="ix-welcome">
                <span class="ix-welcome-wave">👋</span>
                <div class="ix-welcome-title">Welcome to IntelX</div>
                <div>Ask me anything about the company data!</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        for msg in st.session_state.ix_messages:
            avatar = "🤖" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Input (text_input for popover compatibility) ──
    input_col, send_col = st.columns([5, 1])
    with input_col:
        prompt = st.text_input(
            "Ask IntelX",
            placeholder="Ask IntelX Assistant...",
            key="ix_text_input",
            label_visibility="collapsed",
        )
    with send_col:
        send_clicked = st.button(
            "➤", key="ix_send_btn", width="stretch", type="primary"
        )

    if st.session_state.ix_inject:
        prompt = st.session_state.ix_inject
        send_clicked = True
        st.session_state.ix_inject = None

    if (send_clicked or prompt) and prompt and company_name:
        # 1. Capture the query
        user_query = str(prompt).strip()

        # Guard: Check if we just handled this exact query to prevent loops
        if (
            st.session_state.ix_messages
            and st.session_state.ix_messages[-1]["content"] == user_query
            and st.session_state.ix_messages[-1]["role"] == "user"
        ):
            # Already handled in this session run, skip to avoid recursion
            pass
        else:
            # 2. Add to message history
            st.session_state.ix_messages.append({"role": "user", "content": user_query})

        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(user_query)
            with st.chat_message("assistant", avatar="🤖"):
                placeholder = st.empty()
                full_response = ""
                with st.spinner(""):
                    vm = _get_vector_manager()
                    _ensure_vectors_ingested(ticker, vm)
                    agent = _get_chat_agent(company_name)

                    # Extract current dashboard data for immediate context
                    extra_ctx = ""
                    current_data = st.session_state.get("data", {})
                    if current_data:
                        insights = current_data.get("insights", [])
                        if isinstance(insights, list):
                            for ins in insights:
                                if isinstance(ins, dict):
                                    # Handle both structured and list formats
                                    if "finding" in ins:
                                        extra_ctx += f"- {ins.get('category')}: {ins.get('finding')} (Source: {ins.get('source')})\n"
                                    elif "text" in ins:
                                        extra_ctx += f"- {ins.get('category', 'Insight')}: {ins.get('text')}\n"

                        financials = current_data.get("financials", {}).get(
                            "current", {}
                        )
                        if financials:
                            extra_ctx += f"\nFinancial Context: Revenue {financials.get('rev')}, Profit {financials.get('profit')}, Period {financials.get('period')}\n"

                    response = agent.answer_query(
                        query=user_query,
                        ticker=ticker,
                        history=st.session_state.ix_messages[:-1],
                        extra_context=extra_ctx if extra_ctx else None,
                    )
                # Preserving vertical structure and newlines from the LLM
                for part in re.split(r"(\s+)", response):
                    full_response += part
                    # To keep it smooth but respect Markdown rendering, update on words or non-space whitespace
                    if part.strip() or "\n" in part:
                        placeholder.markdown(full_response + "▌")
                        time.sleep(0.005)
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
