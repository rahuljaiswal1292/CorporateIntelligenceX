"""
Agent Pipeline Visualization Component
Futuristic "INTELLIGENCE DISCOVERY SEQUENCE" with brand-aligned glassmorphism.
"""

import streamlit as st
import textwrap


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
    Renders a premium, brand-aligned "Intelligence Discovery Sequence".
    """
    if data is None:
        data = {}

    # Read statuses from session state
    agent_status = st.session_state.get("agent_status", get_default_agent_status())

    # Helper to get status of an agent
    def get_status(agent_key):
        return agent_status.get(agent_key, "pending")

    # Helper to get stage status based on its agents
    def get_stage_info(stage_id):
        if stage_id == "intent":
            search_exists = any(
                k.startswith("company_search_input_") and st.session_state.get(k)
                for k in st.session_state.keys()
            )
            if (
                search_exists
                or data.get("query")
                or st.session_state.get("is_resolving")
            ):
                # Return 'completed' without 'animate' once input is confirmed
                return "success", "completed"
            return "running", "active"

        if stage_id == "resolution":
            s = get_status("master_agent")
            is_paused = st.session_state.get("investigation_paused", False)
            is_complete = st.session_state.get("analysis_complete", False)
            has_name = bool(st.session_state.get("canonical_name"))

            # definitively stop animation if card is printed (paused) or name is already found
            is_done_with_res = is_paused or is_complete or (s == "success" and has_name)

            if s == "running":
                return "running", "active"
            if s == "success" or is_done_with_res:
                if is_done_with_res:
                    return "success", "completed"
                return "running", "active"
            return "pending", "pending"

        mapping = {
            "enrichment": [
                "wikipedia_agent",
                "news_agent",
                "ded_agent",
                "scraper",
                "yahoo_agent",
                "pdf_agent",
            ],
            "vectorizing": ["vectorizer"],
            "synthesis": ["analyst"],
        }

        agents = mapping.get(stage_id, [])
        statuses = [get_status(a) for a in agents]

        if any(s == "error" for s in statuses):
            return "error", "error"
        if any(s == "running" for s in statuses):
            return "running", "active"

        # If any agents are still pending, the stage is pending (unless it's already active/error)
        if not agents or any(s == "pending" for s in statuses):
            return "pending", "pending"
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

        # Only if all agents are success
        if all(s == "success" for s in statuses):
            return "success", "completed"

        return "pending", "pending"

    # Define stages
    stages = [
        {"id": "intent", "label": "Search Input", "icon": "🔍"},
        {"id": "resolution", "label": "Entity Resolution Agent", "icon": "🎯"},
        {
            "id": "enrichment",
            "label": "Data Enrichment Agent",
            "icon": "🌐",
            "is_parallel": True,
        },
        {"id": "vectorizing_stocks", "label": "Stocks & Financials Agent", "icon": "💹"},
        {"id": "vectorizing_neural", "label": "Vectorization Agent", "icon": "🧠"},
        {"id": "synthesis", "label": "Strategic Insights Agent", "icon": "📊"},
    ]

    # Map stock/financials to vectorizing stage ID for logic
    logic_stage_map = {
        "vectorizing_stocks": "vectorizing",
        "vectorizing_neural": "vectorizing",
    }

    # Calculate overall progress for the connector line
    completed_stages = 0
    active_idx = -1
    for i, s in enumerate(stages):
        logic_id = logic_stage_map.get(s["id"], s["id"])
        _, cls = get_stage_info(logic_id)
        if "completed" in cls:
            completed_stages += 1
        elif "active" in cls and active_idx == -1:
            active_idx = i

    progress_percent = (completed_stages / len(stages)) * 100
    if active_idx != -1:
        progress_percent = ((active_idx + 0.5) / len(stages)) * 100

    # Brand Colors
    navy = "#002D62"
    gold = "#FFB600"
    success_green = "#10b981"
    border_color = "rgba(0, 45, 98, 0.15)"

    # CSS for the premium look
    css = textwrap.dedent(
        f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
        
        .pipeline-tracker {{
            font-family: 'Poppins', sans-serif;
            background: white;
            border: 1px solid {border_color};
            border-radius: 20px;
            padding: 40px 30px;
            margin: 20px 0;
            position: relative;
            box-shadow: 0 10px 30px rgba(0, 45, 98, 0.05);
        }}
        
        .nodes-container {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            position: relative;
            z-index: 5;
            min-width: 1000px;
        }}

        .connector-line-bg {{
            position: absolute;
            top: 40px;
            left: 50px;
            right: 50px;
            height: 3px;
            background: #EDF2F7;
            z-index: 1;
        }}

        .connector-line-progress {{
            position: absolute;
            top: 40px;
            left: 50px;
            width: calc({progress_percent}% - 100px);
            height: 3px;
            background: linear-gradient(90deg, {success_green}, {navy});
            z-index: 2;
            transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .node {{
            display: flex;
            flex-direction: column;
            align-items: center;
            flex: 1;
            position: relative;
            z-index: 10;
        }}

        .node-icon-shell {{
            width: 80px;
            height: 80px;
            background: white;
            border: 2px solid #E2E8F0;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 12px;
            transition: all 0.4s ease;
            position: relative;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
            z-index: 5;
        }}

        /* Animations */
        .node.active .node-icon-shell,
        .node.animate .node-icon-shell {{
            animation: breathing-zoom 2.5s ease-in-out infinite;
        }}

        @keyframes breathing-zoom {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.1); }}
        }}

        .node.active .node-icon-shell {{
            border-color: {navy};
            background: #F0F7FF;
            box-shadow: 0 0 25px rgba(0, 45, 98, 0.2);
        }}

        .node.completed .node-icon-shell {{
            border-color: {success_green};
            background: #F0FDF4;
            color: {success_green};
        }}
        
        .node.completed.animate .node-icon-shell {{
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.4);
        }}

        .active-ring {{
            position: absolute;
            inset: -12px;
            border: 3px dotted #10b981;
            border-radius: 50%;
            opacity: 0;
            transition: opacity 0.3s ease;
            animation: rotate-ring 6s linear infinite;
        }}
        
        .node.active .active-ring,
        .node.animate .active-ring {{
            opacity: 1;
        }}
        
        @keyframes rotate-ring {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .node-icon {{
            font-size: 32px;
        }}

        .node-label {{
            font-size: 13px;
            font-weight: 700;
            color: #64748B;
            text-align: center;
            max-width: 120px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .node.active .node-label {{ color: {navy}; }}
        .node.completed .node-label {{ color: {success_green}; }}

        /* Parallel Cluster */
        .parallel-cluster {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 15px;
            width: 320px;
        }}

        .track-node {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            font-weight: 600;
            padding: 6px 12px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            color: #64748B;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .track-node.active {{
            border-color: {navy};
            color: {navy};
            background: #F0F7FF;
            animation: breathing-zoom 2s ease-in-out infinite;
        }}

        .track-node.completed {{
            border-color: {success_green};
            color: {success_green};
            background: #F0FDF4;
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #CBD5E1;
        }}

        .track-node.active .status-dot {{
            background: {navy};
            animation: pulse-dot 1.5s infinite;
        }}

        .track-node.completed .status-dot {{
            background: {success_green};
        }}

        @keyframes pulse-dot {{
            0% {{ box-shadow: 0 0 0 0 rgba(0, 45, 98, 0.4); }}
            70% {{ box-shadow: 0 0 0 6px rgba(0, 45, 98, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(0, 45, 98, 0); }}
        }}
    </style>
    """
    )

    # Build Stage HTML
    nodes_html = ""

    for i, stage in enumerate(stages):
        logic_id = logic_stage_map.get(stage["id"], stage["id"])
        status, css_class = get_stage_info(logic_id)

        # Build Parallel Cluster for Enrichment
        sub_content = ""
        if stage.get("is_parallel"):
            tracks = [
                ("wikipedia_agent", "WIKIPEDIA"),
                ("news_agent", "LATEST NEWS"),
                ("ded_agent", "DFM SCRAPER"),
                ("scraper", "ADX SCRAPER"),
                ("yahoo_agent", "YAHOO FINANCE"),
                ("pdf_agent", "DED FILINGS"),
            ]
            sub_content = '<div class="parallel-cluster">'
            for key, label in tracks:
                s = get_status(key)
                c = (
                    "active"
                    if s == "running"
                    else ("completed" if s == "success" else "pending")
                )
                sub_content += f'<div class="track-node {c}"><div class="status-dot"></div>{label}</div>'
            sub_content += "</div>"

        nodes_html += f"""
        <div class="node {css_class}">
            <div class="node-icon-shell">
                <div class="active-ring"></div>
                <span class="node-icon">{stage['icon']}</span>
            </div>
            <span class="node-label">{stage['label']}</span>
            {sub_content}
        </div>
        """

    # Header label replacement in HTML to unify naming
    sequence_label = "PROGRESS MONITOR"

    # Render with st.html
    full_html = f"""
    {css}
    <div style="font-family:'Poppins',sans-serif; font-size:18px; font-weight:700; color:{navy}; margin-bottom:18px; display:flex; align-items:center; gap:10px;">
        <span style="font-size:22px;">⚡</span> {sequence_label}
    </div>
    <div class="pipeline-tracker">
        <div class="pipeline-scroll-wrapper">
            <div class="nodes-container">
                <div class="connector-line-bg"></div>
                <div class="connector-line-progress"></div>
                {nodes_html}
            </div>
        </div>
    </div>
    """

    st.container().html(full_html)
