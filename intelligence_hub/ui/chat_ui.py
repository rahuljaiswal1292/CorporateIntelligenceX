import os
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
    background: #F8FAFC !important;
    border-radius: 10px !important;
    border: 1px solid #E2E8F0 !important;
    margin-bottom: 8px !important;
    padding: 10px !important;
}
.ix-chat-area [data-testid="stChatMessage"] p {
    font-size: 0.85rem !important;
    line-height: 1.5 !important;
    color: #1E293B !important;
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

        c1, c2 = st.columns(2)
        with c1:
            if st.button("📊 Revenue", key="ix_btn_rev", use_container_width=True):
                st.session_state.ix_inject = (
                    f"What are the latest revenue trends for {company_name}?"
                )
        with c2:
            if st.button("⚠️ Risks", key="ix_btn_risk", use_container_width=True):
                st.session_state.ix_inject = (
                    f"What are the key risks for {company_name}?"
                )

        c3, c4 = st.columns(2)
        with c3:
            if st.button("🏛️ Strategy", key="ix_btn_strat", use_container_width=True):
                st.session_state.ix_inject = (
                    f"What is the strategic vision for {company_name}?"
                )
        with c4:
            if st.button("🗞️ News", key="ix_btn_news", use_container_width=True):
                st.session_state.ix_inject = (
                    f"Summarize recent news for {company_name}."
                )

        # ── Knowledge Inventory ──
        with st.expander("📂 Knowledge Base", expanded=False):
            vm = _get_vector_manager()
            try:
                results = vm.collection.get(
                    where={"ticker": ticker.upper()}, include=["metadatas"]
                )
                if results["metadatas"]:
                    sources = {m.get("source", "Unknown") for m in results["metadatas"]}
                    for src in sorted(list(sources)):
                        icon = (
                            "📄"
                            if src.endswith(".pdf")
                            else ("📊" if src.endswith(".csv") else "📝")
                        )
                        st.markdown(
                            f'<div class="ix-inventory-item">{icon} {src}</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f'<div class="ix-inventory-count">Total Chunks: {len(results["metadatas"])}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("No sources indexed yet.")
            except Exception:
                st.caption("Indexing in progress...")

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
            "➤", key="ix_send_btn", use_container_width=True, type="primary"
        )

    if st.session_state.ix_inject:
        prompt = st.session_state.ix_inject
        send_clicked = True
        st.session_state.ix_inject = None

    if (send_clicked or prompt) and prompt and company_name:
        st.session_state.ix_messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                placeholder = st.empty()
                full_response = ""
                with st.spinner(""):
                    vm = _get_vector_manager()
                    _ensure_vectors_ingested(ticker, vm)
                    agent = _get_chat_agent(company_name)
                    response = agent.answer_query(
                        query=prompt,
                        ticker=ticker,
                        history=st.session_state.ix_messages[:-1],
                    )
                for word in response.split():
                    full_response += word + " "
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
            use_container_width=True,
            type="secondary",
        ):
            st.session_state.ix_messages = []
            st.rerun()
