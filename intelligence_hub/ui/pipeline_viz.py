"""
Agent Pipeline Visualization Component
Horizontal stepper showing execution flow with parallel stage support.
"""

import streamlit as st


def render_agent_pipeline(data: dict, show_details: bool = False):
    """
    Renders a horizontal stepper pipeline showing agent execution flow.
    Parallel agents are shown inside a bordered container within one step.
    """

    if data is None:
        data = {}

    logs = data.get("logs", [])
    enrichments = data.get("enrichments", {})

    # Pipeline stages with domain-relevant names
    stages = [
        {"label": "Name Resolution", "agents": ["Master Agent"], "icon": "🎯", "parallel": False},
        {"label": "Profile Enrichment", "agents": ["Wikipedia Agent", "News Agent", "DED Agent"], "icon": "🔄", "parallel": True},
        {"label": "Stocks & Filings", "agents": ["Scraper Orchestrator"], "icon": "�", "parallel": False},
        {"label": "Financial Statements", "agents": ["Vectorizer Agent", "PDF Agent"], "icon": "📑", "parallel": False},
        {"label": "Insights Generation", "agents": ["Analyst Agent"], "icon": "💡", "parallel": False},
    ]

    def get_agent_status(agent_name):
        for log in logs:
            log_lower = log.lower()
            name_lower = agent_name.lower()
            if name_lower in log_lower or name_lower.replace(" ", "_") in log_lower:
                if any(w in log_lower for w in ["completed", "success", "done"]):
                    return "success"
                if any(w in log_lower for w in ["failed", "error"]):
                    return "error"
        if "Wikipedia" in agent_name and enrichments.get("wikipedia"):
            return "success"
        if "News" in agent_name and enrichments.get("news"):
            return "success"
        if "DED" in agent_name and enrichments.get("ded"):
            return "success"
        return "pending"

    def get_stage_status(agents):
        statuses = [get_agent_status(a) for a in agents]
        if any(s == "error" for s in statuses):
            return "error"
        if all(s == "success" for s in statuses):
            return "success"
        return "pending"

    # Status styling
    def status_style(status):
        if status == "success":
            return {"dot": "#10b981", "border": "#059669", "label": "#065f46", "agent": "#047857", "check": "✓"}
        elif status == "error":
            return {"dot": "#ef4444", "border": "#dc2626", "label": "#991b1b", "agent": "#b91c1c", "check": "✗"}
        else:
            return {"dot": "#cbd5e1", "border": "#94a3b8", "label": "#64748b", "agent": "#94a3b8", "check": "○"}

    # Build step HTML
    step_htmls = []
    for idx, stage in enumerate(stages):
        st_status = get_stage_status(stage["agents"])
        s = status_style(st_status)
        is_parallel = stage["parallel"]

        # Agents display
        if is_parallel:
            # Build individual agent badges inside a container
            agent_badges = ""
            for a in stage["agents"]:
                a_status = get_agent_status(a)
                a_s = status_style(a_status)
                short = a.replace(" Agent", "")
                agent_badges += f'''
                    <div style="
                        display:flex;align-items:center;gap:4px;
                        background:{'#ecfdf5' if a_status=='success' else '#fef2f2' if a_status=='error' else '#f8fafc'};
                        border:1px solid {'#a7f3d0' if a_status=='success' else '#fecaca' if a_status=='error' else '#e2e8f0'};
                        border-radius:4px;padding:2px 6px;
                    ">
                        <span style="font-size:9px;color:{a_s['agent']};font-weight:700;">{a_s['check']}</span>
                        <span style="font-size:9px;color:{a_s['label']};font-weight:600;white-space:nowrap;">{short}</span>
                    </div>
                '''

            agents_html = f'''
                <div style="
                    border:1px dashed {'#10b981' if st_status=='success' else '#94a3b8'};
                    border-radius:6px;
                    padding:6px;
                    margin-top:6px;
                    background:{'rgba(16,185,129,0.03)' if st_status=='success' else 'rgba(148,163,184,0.05)'};
                    display:flex;flex-direction:column;gap:3px;
                    align-items:center;
                ">
                    {agent_badges}
                    <div style="font-size:7px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.8px;margin-top:1px;font-weight:700;">parallel</div>
                </div>
            '''
        else:
            agent_names = " → ".join(a.replace(" Agent", "").replace(" Orchestrator", "") for a in stage["agents"])
            agents_html = f'<div style="font-size:10px;color:{s["agent"]};line-height:1.4;margin-top:4px;">{agent_names}</div>'

        step_htmls.append(f"""
            <div style="display:flex;flex-direction:column;align-items:center;flex:1;min-width:0;">
                <div style="
                    width:34px;height:34px;border-radius:50%;
                    background:{s['dot']};border:3px solid {s['border']};
                    display:flex;align-items:center;justify-content:center;
                    font-size:13px;color:white;font-weight:700;
                    box-shadow:0 2px 6px rgba(0,0,0,0.12);
                    z-index:2;position:relative;
                ">{s['check']}</div>
                <div style="margin-top:6px;text-align:center;font-family:'Poppins',sans-serif;">
                    <div style="font-size:11px;font-weight:700;color:{s['label']};margin-bottom:1px;">{stage['label']}</div>
                    {agents_html}
                </div>
            </div>
        """)

    # Build connectors + steps
    items = []
    for i, step_html in enumerate(step_htmls):
        items.append(step_html)
        if i < len(stages) - 1:
            curr = get_stage_status(stages[i]["agents"])
            nxt = get_stage_status(stages[i + 1]["agents"])
            if curr == "success" and nxt == "success":
                lc = "#10b981"
            elif curr == "success":
                lc = "#93c5fd"
            else:
                lc = "#e2e8f0"
            items.append(f'''
                <div style="flex:0.4;display:flex;align-items:flex-start;padding-top:16px;">
                    <div style="height:2px;width:100%;background:{lc};border-radius:2px;"></div>
                </div>
            ''')

    full_html = "".join(items)

    st.html(f"""
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
    """)
