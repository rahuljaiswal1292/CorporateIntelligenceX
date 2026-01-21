import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_header():
    """Renders the main dashboard header with Greeting and Process Flow."""
    st.title("CorporateIntelligenceX")
    st.markdown("### 360° Automated Banking Intelligence Agent")
    st.markdown("---")
    
    # Process Explanation Box
    st.info("""
    **👋 Welcome to your Banking Intelligence Terminal.**
    
    This agent automates the due diligence process in 4 steps:
    1.  **Identify**: Resolves the company entity from stock exchanges (ADX/DFM).
    2.  **Scrape**: Fetches real-time annual reports and financial disclosures.
    3.  **Vectorize**: Indexes documents for semantic search (RAG).
    4.  **Analyze**: Generates strategic banking opportunities and risk signals.
    """)

def render_progress_chain(stage: int):
    """
    Renders the specific XML/DIv structure requested for the progress steps.
    """
    steps = [
        {"icon": "🔍", "label": "Identify"},
        {"icon": "🕷️", "label": "Scrape"},
        {"icon": "🧠", "label": "Vectorize"},
        {"icon": "📊", "label": "Analyze"},
        {"icon": "✅", "label": "Ready"}
    ]
    
    html = '<div class="progress-container"><div class="progress-track"></div>'
    
    for i, step in enumerate(steps):
        status_class = ""
        if i < stage - 1:
            status_class = "completed"
        elif i == stage - 1:
            status_class = "active"
            
        # Minified HTML to avoid markdown parsing weirdness
        html += f'<div class="progress-step {status_class}"><span class="progress-step-icon">{step["icon"]}</span><span>{step["label"]}</span></div>'
        
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def render_company_profile(data):
    """Renders the Expanded Company Overview."""
    meta = data["meta"]
    st.subheader(f"{meta['name']}")
    
    # 7-10 lines description area
    st.caption("COMPANY OVERVIEW")
    st.write(meta["description"])
    
    # Socials / Web
    st.markdown(f"**Official Website:** [{meta['website']}]({meta['website']})")
    
    socials = meta.get("socials", {})
    links = " | ".join([f"[{k}]({v})" for k,v in socials.items()])
    st.markdown(f"**Social Media:** {links}")

    st.markdown("---")
    
    # Side-by-side: Key Shareholders & Exchange Info
    c1, c2 = st.columns([3, 2]) # Adjusted ratio for better table width
    with c1:
        st.caption("KEY SHAREHOLDERS")
        if "shareholders" in meta and isinstance(meta["shareholders"], list):
            # Custom HTML Table for Shareholders (Matching Peer Competitors Theme)
            sh_data = meta["shareholders"]
            
            # Flattened HTML for Shareholders Table
            html_rows = ""
            for i, row in enumerate(sh_data):
                bg_color = "#FFF9E6" if i % 2 == 0 else "#FFF0C2"
                name = row.get("Name", "-")
                stake = row.get("%", "-")
                html_rows += f"""<tr style="background-color:{bg_color}; border-bottom:1px solid #E2E8F0;"><td style="padding:10px 12px; color:#002D62; font-weight:600; font-size:0.9rem;">{name}</td><td style="padding:10px 12px; color:#002D62; font-size:0.9rem; text-align:right;">{stake}</td></tr>"""

            html = f"""<table style="width:100%; border-collapse:collapse; font-family:sans-serif; border-radius:8px; overflow:hidden; border:1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);"><thead><tr style="background-color:#002D62; color:#FFFFFF;"><th style="padding:12px; text-align:left; font-weight:700; border-bottom:3px solid #FFB600; font-size:0.9rem;">Shareholder</th><th style="padding:12px; text-align:right; font-weight:700; border-bottom:3px solid #FFB600; font-size:0.9rem;">Stake</th></tr></thead><tbody>{html_rows}</tbody></table>"""
            
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.write(meta.get("shareholders", "-"))
            
    with c2:
        st.markdown("""
        <div style="margin-bottom: 15px;">
            <div style="color:#64748B; font-size:0.85rem; font-weight:700; text-transform:uppercase; margin-bottom:4px;">🏢 Industry</div>
            <div style="color:#0F172A; font-size:1.1rem; font-weight:700;">""" + meta.get('sector', '-') + """</div>
        </div>
        <div style="margin-bottom: 15px;">
            <div style="color:#64748B; font-size:0.85rem; font-weight:700; text-transform:uppercase; margin-bottom:4px;">📉 Listing Info</div>
            <div style="color:#0F172A; font-size:1.1rem; font-weight:700;">""" + f"{meta.get('exchange', '-')} : {meta.get('ticker', '-')}" + """</div>
        </div>
        <div>
            <div style="color:#64748B; font-size:0.85rem; font-weight:700; text-transform:uppercase; margin-bottom:4px;">📅 Established</div>
            <div style="color:#0F172A; font-size:1.1rem; font-weight:700;">""" + meta.get('est_date', '-') + """</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

def render_financials_detailed(data):
    """Renders Financials split into Yearly and Quarterly views using Custom HTML Cards."""
    f = data["financials"]
    curr = f["current"]
    last_y = f.get("last_year", {})
    last_q = f.get("last_quarter", {})
    
    # --- Helper Helper for Custom Metric Card ---
    def make_metric_card(label, value, delta=None, sub=None):
        delta_html = ""
        if delta:
            # Check for positive/negative trend
            is_pos = "+" in str(delta) or "↑" in str(delta)
            color = "#16A34A" if is_pos else "#DC2626"
            delta_html = f"<div style='color: {color}; font-size: 0.95rem; font-weight: 700; margin-top: 8px;'>{delta} <span style='color: #64748B; font-size: 0.8rem; font-weight: 600;'>{sub or ''}</span></div>"
        
        return f"""<div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: center; height: 100%;"><div style="color: #0F172A; font-size: 0.9rem; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.02em;">{label}</div><div style="color: #002D62; font-size: 1.7rem; font-weight: 800; line-height: 1.1;">{value}</div>{delta_html}</div>"""

    # 1. Yearly Performance
    st.subheader(f"📊 Yearly Performance ({last_y['period']} vs {curr['period']})")
    
    # HTML Grid for Yearly - FLATTENED STRING
    st.markdown(f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px;">{make_metric_card("Revenue (Current)", curr.get("rev"), curr.get("trend"))}{make_metric_card("Revenue (Last Yr)", last_y.get("rev"), "Hist")}{make_metric_card("Net Profit (Current)", curr.get("profit"), "")}{make_metric_card("Net Profit (Last Yr)", last_y.get("profit"), "Hist")}</div>""", unsafe_allow_html=True)
    
    # 2. Quarterly Performance
    st.subheader(f"📉 Latest Quarter Performance ({last_q.get('period', 'Q3')})")
    
    # HTML Grid for Quarterly - FLATTENED STRING
    st.markdown(f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px;">{make_metric_card("Revenue (Qtr)", last_q.get("rev"), last_q.get("rev_gro", ""))}{make_metric_card("Profit (Qtr)", last_q.get("profit"), last_q.get("prof_gro", ""))}{make_metric_card("Share Price", curr.get("price"), curr.get("trend"))}{make_metric_card("Market Cap", "AED --", "Est")}</div>""", unsafe_allow_html=True)

    # Risk Metrics below (Updated to use Custom Cards for Visibility)
    st.caption("RISK & COMPLIANCE SIGNALS")
    r = data["risk"]
    
    # HTML Grid for Risk - FLATTENED
    st.markdown(f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px;">{make_metric_card("Debt/Equity", r.get("debt_equity"), "Leverage")}{make_metric_card("Credit Rating", r.get("credit_rating"), "External")}{make_metric_card("Interest Cover", r.get("interest_cover"), "Solvency")}{make_metric_card("Altman Z-Score", "Safe", "Est")}</div>""", unsafe_allow_html=True)
    
    st.markdown("---")

def render_chart(data):
    """Renders the candlestick stock chart."""
    st.subheader("📈 Stock Performance (1Y)")
    
    chart_data = data.get("chart", {})
    if not chart_data:
        st.warning("No chart data available.")
        return

    fig = go.Figure(data=[go.Candlestick(
        x=chart_data["dates"],
        open=chart_data["open"],
        high=chart_data["high"],
        low=chart_data["low"],
        close=chart_data["close"],
        increasing_line_color= '#10B981', 
        decreasing_line_color= '#EF4444' 
    )])
    
    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        height=400, # Resized for better fit
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#0F172A'), # Global Text
        xaxis=dict(
            tickfont=dict(color='#0F172A', size=12),
            title_font=dict(color='#0F172A')
        ),
        yaxis=dict(
             tickfont=dict(color='#0F172A', size=12),
             title_font=dict(color='#0F172A')
        )
    )
    st.plotly_chart(fig, use_container_width=True)

def render_competitors(data):
    """Renders the competitor analysis table using Custom HTML for styling control."""
    st.subheader("⚔️ Peer Competitors")
    comps = data.get("competitors", [])
    if not comps:
        st.info("No competitor data found.")
        return

    # Convert to HTML Table logic
    headers = ["Company", "Mkt Cap", "P/E", "Rev Growth"]
    
    # Flattened HTML to avoid Markdown Code Block interpretation
    html_rows = ""
    for i, row in enumerate(comps):
        bg_color = "#FFF9E6" if i % 2 == 0 else "#FFF0C2"
        html_rows += f"""<tr style="background-color:{bg_color}; border-bottom:1px solid #E2E8F0;"><td style="padding:12px; color:#002D62; font-weight:600;">{row["Company"]}</td><td style="padding:12px; color:#002D62;">{row["Mkt Cap"]}</td><td style="padding:12px; color:#002D62;">{row["P/E"]}</td><td style="padding:12px; color:#002D62;">{row["Rev Growth"]}</td></tr>"""

    html = f"""<table style="width:100%; border-collapse:collapse; font-family:sans-serif; border-radius:8px; overflow:hidden; border:1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);"><thead><tr style="background-color:#002D62; color:#FFFFFF;"><th style="padding:14px; text-align:left; font-weight:700; border-bottom:3px solid #FFB600;">Company</th><th style="padding:14px; text-align:left; font-weight:700; border-bottom:3px solid #FFB600;">Mkt Cap</th><th style="padding:14px; text-align:left; font-weight:700; border-bottom:3px solid #FFB600;">P/E</th><th style="padding:14px; text-align:left; font-weight:700; border-bottom:3px solid #FFB600;">Rev Growth</th></tr></thead><tbody>{html_rows}</tbody></table>"""
    
    st.markdown(html, unsafe_allow_html=True)

def render_insights_strategic(data):
    """Renders the STRATEGIC & RM INSIGHTS."""
    st.markdown("### 🚀 Strategic & RM Insights")
    st.caption("AI-Generated Banking Opportunities & Risk Triggers")
    
    insights = data.get("insights", [])
    if not insights:
        st.info("Generating insights...")
        return
        
    for item in insights:
        cat = item.get("category", "General")
        finding = item.get("finding", "")
        source = item.get("source", "")
        trigger = item.get("trigger", "")
        action = item.get("action", "")
        
        css_class = ""
        if "Lending" in cat: css_class = "cat-lending"
        elif "Trade" in cat: css_class = "cat-trade"
        elif "Operational" in cat: css_class = "cat-ops"
        elif "KYC" in cat: css_class = "cat-kyc"
        else: css_class = "cat-strategy"
        
        html = f"""
        <div class="insight-card {css_class}">
            <h4>{cat}</h4>
            <div class="insight-meta">
                <span>📍 Finding: {finding}</span>
                <span>⚡ Trigger: {trigger}</span>
            </div>
            <div class="insight-action-box">
                <span class="insight-action-title">💡 RM Action:</span>
                <span class="insight-action-text">"{action}"</span>
            </div>
            <div style="margin-top:5px; font-size:0.75rem; color:#94a3b8;">
                Source: {source}
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

def render_sources(data):
    """Renders the list of extracted reports."""
    st.markdown("### 📚 Extracted Report Sources")
    sources = data.get("sources", [])
    if sources:
        for s in sources:
            st.markdown(f"- [{s['title']}]({s['url']})")
    else:
        st.markdown("- *No public reports linked for this simulated entity.*")
