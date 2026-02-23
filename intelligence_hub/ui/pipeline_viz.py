"""
Agent Pipeline Visualization Component
Horizontal stepper with real-time status from session state.
"""

import streamlit as st


# Default agent status structure
def get_default_agent_status():
    """Returns the default agent status dict with all agents pending."""
    return {
        "master_agent": "pending",
        "wikipedia_agent": "pending",
        "news_agent": "pending",
        "ded_agent": "pending",
        "scraper": "pending",
        "vectorizer": "pending",
        "pdf_agent": "pending",
        "analyst": "pending",
    }


def render_agent_pipeline(data: dict = None, show_details: bool = False):
    """
    Renders a horizontal stepper pipeline.
    Reads agent_status from st.session_state for real-time updates.
    """

    if data is None:
        data = {}

    # Read statuses from session state (set by workflow callbacks)
    agent_status = st.session_state.get("agent_status", get_default_agent_status())

    # Pipeline stages mapped to agent keys
    stages = [
        {
            "label": "Name Resolution",
            "agents": [("master_agent", "Master")],
            "parallel": False,
        },
        {
            "label": "Profile Enrichment",
            "agents": [
                ("wikipedia_agent", "Wikipedia"),
                ("news_agent", "News"),
                ("ded_agent", "DED"),
            ],
            "parallel": True,
        },
        {
            "label": "Stocks & Filings",
            "agents": [("scraper", "Scraper")],
            "parallel": False,
        },
        {
            "label": "Financial Statements",
            "agents": [("vectorizer", "Vectorizer"), ("pdf_agent", "PDF")],
            "parallel": False,
        },
        {
            "label": "Insights Generation",
            "agents": [("analyst", "Analyst")],
            "parallel": False,
        },
    ]

    def get_status(agent_key):
        return agent_status.get(agent_key, "pending")

    def get_stage_status(agents):
        statuses = [get_status(a[0]) for a in agents]
        if any(s == "error" for s in statuses):
            return "error"
        if all(s == "success" for s in statuses):
            return "success"
        if any(s == "running" for s in statuses):
            return "running"
        return "pending"

    def style_for(status):
        if status == "success":
            return {
                "bg": "#10b981",
                "bdr": "#059669",
                "lbl": "#065f46",
                "txt": "#047857",
                "ico": "✓",
                "badge_bg": "#ecfdf5",
                "badge_bdr": "#a7f3d0",
            }
        elif status == "error":
            return {
                "bg": "#ef4444",
                "bdr": "#dc2626",
                "lbl": "#991b1b",
                "txt": "#b91c1c",
                "ico": "✗",
                "badge_bg": "#fef2f2",
                "badge_bdr": "#fecaca",
            }
        elif status == "running":
            return {
                "bg": "#3b82f6",
                "bdr": "#2563eb",
                "lbl": "#1e40af",
                "txt": "#2563eb",
                "ico": "⟳",
                "badge_bg": "#eff6ff",
                "badge_bdr": "#93c5fd",
            }
        else:
            return {
                "bg": "#cbd5e1",
                "bdr": "#94a3b8",
                "lbl": "#64748b",
                "txt": "#94a3b8",
                "ico": "○",
                "badge_bg": "#f8fafc",
                "badge_bdr": "#e2e8f0",
            }

    # CSS animation for running state
    pulse_css = """
    @keyframes pulse-dot {
        0%, 100% { transform: scale(1); box-shadow: 0 2px 6px rgba(59,130,246,0.3); }
        50% { transform: scale(1.15); box-shadow: 0 2px 12px rgba(59,130,246,0.5); }
    }
    """

    # Build step HTML
    step_htmls = []
    for idx, stage in enumerate(stages):
        ss = get_stage_status(stage["agents"])
        s = style_for(ss)
        is_parallel = stage["parallel"]

        # Pulse animation for running dots
        anim = (
            "animation:pulse-dot 1.2s ease-in-out infinite;" if ss == "running" else ""
        )

        # Build agent display
        if is_parallel:
            agent_badges = ""
            for key, name in stage["agents"]:
                a_s = style_for(get_status(key))
                a_anim = (
                    "animation:pulse-dot 1.2s ease-in-out infinite;"
                    if get_status(key) == "running"
                    else ""
                )
                agent_badges += f"""
                    <div style="
                        display:flex;align-items:center;gap:4px;
                        background:{a_s['badge_bg']};
                        border:1px solid {a_s['badge_bdr']};
                        border-radius:4px;padding:2px 6px;{a_anim}
                    ">
                        <span style="font-size:9px;color:{a_s['txt']};font-weight:700;">{a_s['ico']}</span>
                        <span style="font-size:9px;color:{a_s['lbl']};font-weight:600;white-space:nowrap;">{name}</span>
                    </div>
                """

            agents_html = f"""
                <div style="
                    border:1px dashed {s['bdr']};
                    border-radius:6px;
                    padding:6px;margin-top:6px;
                    background:rgba(0,0,0,0.01);
                    display:flex;flex-direction:column;gap:3px;
                    align-items:center;
                ">
                    {agent_badges}
                    <div style="font-size:7px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.8px;margin-top:1px;font-weight:700;">parallel</div>
                </div>
            """
        else:
            agent_names = " → ".join(name for _, name in stage["agents"])
            agents_html = f'<div style="font-size:10px;color:{s["txt"]};line-height:1.4;margin-top:4px;">{agent_names}</div>'

        step_htmls.append(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:0;">
                <div style="
                    width:34px;height:34px;border-radius:50%;
                    background:{s['bg']};border:3px solid {s['bdr']};
                    display:flex;align-items:center;justify-content:center;
                    font-size:13px;color:white;font-weight:700;
                    box-shadow:0 2px 6px rgba(0,0,0,0.12);
                    z-index:2;position:relative;{anim}
                ">{s['ico']}</div>
                <div style="margin-top:6px;text-align:center;font-family:'Poppins',sans-serif;">
                    <div style="font-size:11px;font-weight:700;color:{s['lbl']};margin-bottom:1px;">{stage['label']}</div>
                    {agents_html}
                </div>
            </div>
        """
        )

    # Connectors
    items = []
    for i, step_html in enumerate(step_htmls):
        items.append(step_html)
        if i < len(stages) - 1:
            curr = get_stage_status(stages[i]["agents"])
            nxt = get_stage_status(stages[i + 1]["agents"])
            if curr == "success" and nxt in ("success", "running"):
                lc = "#10b981"
            elif curr == "success":
                lc = "#93c5fd"
            else:
                lc = "#e2e8f0"
            items.append(
                f"""
                <div style="flex:0.4;display:flex;align-items:flex-start;padding-top:16px;">
                    <div style="height:2px;width:100%;background:{lc};border-radius:2px;"></div>
                </div>
            """
            )

    full_html = "".join(items)

    st.html(
        f"""
    <style>{pulse_css}</style>
    <div style="
        background:linear-gradient(135deg,#f8fafc 0%,#f1f5f9 100%);
        border:1px solid #e2e8f0;
        border-radius:12px;
        padding:20px 24px 16px 24px;
        margin-bottom:20px;
        box-shadow:0 2px 8px rgba(0,0,0,0.04);
    ">
        <div style="display:flex;align-items:flex-start;gap:0;">
            {full_html}
        </div>
    </div>
    """
    )
