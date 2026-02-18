import streamlit as st
import pandas as pd
import plotly.graph_objects as go

logo_url = "https://www.emiratesnbd.com/-/media/enbd/images/logos/favicon.png"


def render_header():
    """Renders the main dashboard header with Greeting and Process Flow."""
    st.markdown(
        f"""
            <div style="display: flex; align-items: center; gap: 5px;">
            <img src="{logo_url}" style="width: 50px; height: 50px; border-radius: 8px;">
            <h1 style="margin: 0;">CorporateIntelligence<span style="color:blue">X</span></h1>
            </div>
            """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='color:blue; margin-left: 58px; margin-top: -3px;' id='360-automated-web-agent'> 360° Automated Web Agent</h4>",
        unsafe_allow_html=True,
    )
    # st.markdown("---")

    # Process Explanation Box
    st.html(
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
    """
    )


def render_progress_chain(stage: int):
    """
    Renders the progress chain showing workflow stages with a modern, elegant design.
    Supports parallel execution visualization.
    """
    # Define the flow of steps with parallel group
    steps = [
        {"icon": "🏷️", "label": "Canonical + SERP", "stage": 1},
        {
            "type": "parallel",
            "stage": 2,
            "items": [
                {"icon": "⚡", "label": "Enrichment"},
                {"icon": "🕷️", "label": "Scraping"}
            ]
        },
        {"icon": "🧠", "label": "Vectorization", "stage": 3},
        {"icon": "📊", "label": "Analysis", "stage": 4},
    ]
    
    html = '<div class="pipeline-wrapper">'
    html += '<div class="pipeline-track">'
    
    for i, step in enumerate(steps):
        # Determine status base
        status = "pending"
        if stage > step["stage"]:
            status = "completed"
        elif stage == step["stage"]:
            status = "active"
            
        if step.get("type") == "parallel":
            # Render Parallel Group
            html += '<div class="pipeline-parallel-group">'
            for item in step["items"]:
                # Render sub-item (inherits group status for now)
                pulse = "<div class='step-pulse'></div>" if status == "active" else ""
                
                parallel_html = f'<div class="pipeline-step {status} parallel-item">'
                parallel_html += f'<div class="step-indicator small"><span class="step-icon">{item["icon"]}</span>{pulse}</div>'
                parallel_html += f'<div class="step-content side"><span class="step-label">{item["label"]}</span></div>'
                parallel_html += '</div>'
                html += parallel_html
            html += '</div>'
        else:
            # Render Single Step
            pulse = "<div class='step-pulse'></div>" if status == "active" else ""
            sub_items = f'<div class="step-subitems">{" • ".join(step["sub_items"])}</div>' if "sub_items" in step else ""
            
            step_html = f'<div class="pipeline-step {status}">'
            step_html += f'<div class="step-indicator"><span class="step-icon">{step["icon"]}</span>{pulse}</div>'
            step_html += f'<div class="step-content"><span class="step-label">{step["label"]}</span>{sub_items}</div>'
            step_html += '</div>'
            html += step_html
        
        # Connector (if not last step)
        if i < len(steps) - 1:
            conn_status = "completed" if status == "completed" else "pending"
            html += f'<div class="pipeline-connector {conn_status}"></div>'
            
    html += '</div></div>'
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
    links = " | ".join([f"[{k}]({v})" for k, v in socials.items()])
    st.markdown(f"**Social Media:** {links}")

    st.markdown("---")

    # Side-by-side: Key Shareholders & Exchange Info
    c1, c2 = st.columns([3, 2])  # Adjusted ratio for better table width
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
        st.markdown(
            """
        <div style="margin-bottom: 15px;">
            <div style="color:#64748B; font-size:0.85rem; font-weight:700; text-transform:uppercase; margin-bottom:4px;">🏢 Industry</div>
            <div style="color:#0F172A; font-size:1.1rem; font-weight:700;">"""
            + meta.get("sector", "-")
            + """</div>
        </div>
        <div style="margin-bottom: 15px;">
            <div style="color:#64748B; font-size:0.85rem; font-weight:700; text-transform:uppercase; margin-bottom:4px;">📉 Listing Info</div>
            <div style="color:#0F172A; font-size:1.1rem; font-weight:700;">"""
            + f"{meta.get('exchange', '-')} : {meta.get('ticker', '-')}"
            + """</div>
        </div>
        <div>
            <div style="color:#64748B; font-size:0.85rem; font-weight:700; text-transform:uppercase; margin-bottom:4px;">📅 Established</div>
            <div style="color:#0F172A; font-size:1.1rem; font-weight:700;">"""
            + meta.get("est_date", "-")
            + """</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("---")


def render_financials_detailed(data):
    """Renders Financials split into Yearly and Quarterly views using Custom HTML Cards."""
    f = data["financials"]
    curr = f["current"]
    last_y = f.get("last_year", {})
    last_q = f.get("last_quarter", {})

    # --- Helper Helper for Custom Metric Card ---
    def make_metric_card(label, value, delta=None, sub=None):
        if value is None:
            value = "-"

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
    st.markdown(
        f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px;">{make_metric_card("Revenue (Current)", curr.get("rev"), curr.get("trend"))}{make_metric_card("Revenue (Last Yr)", last_y.get("rev"), "Hist")}{make_metric_card("Net Profit (Current)", curr.get("profit"), "")}{make_metric_card("Net Profit (Last Yr)", last_y.get("profit"), "Hist")}</div>""",
        unsafe_allow_html=True,
    )

    # 2. Quarterly Performance
    st.subheader(f"📉 Latest Quarter Performance ({last_q.get('period', 'Q3')})")

    # HTML Grid for Quarterly - FLATTENED STRING
    st.markdown(
        f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px;">{make_metric_card("Revenue (Qtr)", last_q.get("rev"), last_q.get("rev_gro", ""))}{make_metric_card("Profit (Qtr)", last_q.get("profit"), last_q.get("prof_gro", ""))}{make_metric_card("Share Price", curr.get("price"), curr.get("trend"))}{make_metric_card("Market Cap", "AED --", "Est")}</div>""",
        unsafe_allow_html=True,
    )

    # Risk Metrics below (Updated to use Custom Cards for Visibility)
    st.caption("RISK & COMPLIANCE SIGNALS")
    r = data["risk"]

    # HTML Grid for Risk - FLATTENED
    st.markdown(
        f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 20px;">{make_metric_card("Debt/Equity", r.get("debt_equity"), "Leverage")}{make_metric_card("Credit Rating", r.get("credit_rating"), "External")}{make_metric_card("Interest Cover", r.get("interest_cover"), "Solvency")}{make_metric_card("Altman Z-Score", "Safe", "Est")}</div>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")


def render_chart(data):
    """Renders the candlestick stock chart."""
    st.subheader("📈 Stock Performance (1Y)")

    chart_data = data.get("chart", {})
    if not chart_data:
        st.warning("No chart data available.")
        return

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=chart_data["dates"],
                open=chart_data["open"],
                high=chart_data["high"],
                low=chart_data["low"],
                close=chart_data["close"],
                increasing_line_color="#10B981",
                decreasing_line_color="#EF4444",
            )
        ]
    )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        height=400,  # Resized for better fit
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#0F172A"),  # Global Text
        xaxis=dict(
            tickfont=dict(color="#0F172A", size=12), title_font=dict(color="#0F172A")
        ),
        yaxis=dict(
            tickfont=dict(color="#0F172A", size=12), title_font=dict(color="#0F172A")
        ),
    )
    st.plotly_chart(fig, use_container_width=True, key="stock_performance_chart")


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
        if "Lending" in cat:
            css_class = "cat-lending"
        elif "Trade" in cat:
            css_class = "cat-trade"
        elif "Operational" in cat:
            css_class = "cat-ops"
        elif "KYC" in cat:
            css_class = "cat-kyc"
        else:
            css_class = "cat-strategy"

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


def render_pdf_analysis(data):
    """
    Renders the PDF Analysis section from the 'pdf_results' in data.
    """
    if not data or "pdf_results" not in data or not data["pdf_results"]:
        return

    st.markdown("### 📄 Document Analysis")
    st.markdown("Insights extracted from internal documents:")

    results = data["pdf_results"]

    for res in results:
        file_name = res.get("file", "Unknown Document")
        analysis = res.get("analysis", {})

        with st.expander(f"📂 {file_name}", expanded=True):
            cols = st.columns(len(analysis))
            # Handle case where analysis might be empty
            if not analysis:
                st.info("No insights extracted.")
                continue

            # Display key-value pairs
            # If too many keys, columns might be too narrow.
            # Let's use a dynamic grid or just vertical list if > 3
            if len(analysis) > 3:
                for category, text in analysis.items():
                    st.markdown(f"**{category}**")
                    st.info(text)
            else:
                for i, (category, text) in enumerate(analysis.items()):
                    with cols[i]:
                        st.markdown(f"**{category}**")
                        st.info(text)


def render_references(data):
    """Renders a comprehensive references section showing all sources used in the analysis"""
    st.markdown("### 📚 References & Sources")
    st.markdown("*All reference materials used in preparing this intelligence report*")
    
    # Create tabs for different source types
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 SERP Links", "📰 News Sources", "📖 Wikipedia", "🌐 DED & Official"])
    
    # Tab 1: SERP Links
    with tab1:
        serp_links = data.get("serp_links", [])
        if serp_links:
            st.markdown(f"**{len(serp_links)} search results analyzed**")
            for idx, link in enumerate(serp_links, 1):
                if isinstance(link, dict):
                    title = link.get("title", "Untitled")
                    url = link.get("link", "#")
                    snippet = link.get("snippet", "")
                    
                    with st.expander(f"{idx}. {title}", expanded=False):
                        st.markdown(f"**URL:** [{url}]({url})")
                        if snippet:
                            st.markdown(f"**Snippet:** {snippet}")
                else:
                    st.markdown(f"{idx}. [{link}]({link})")
        else:
            st.info("No SERP links available")
    
    # Tab 2: News Sources
    with tab2:
        news_sources = data.get("enrichments", {}).get("news", {}).get("sources", [])
        news_articles = data.get("news_articles", [])
        
        if news_sources or news_articles:
            sources_to_display = news_sources if news_sources else news_articles
            st.markdown(f"**{len(sources_to_display)} news articles analyzed**")
            
            for idx, article in enumerate(sources_to_display, 1):
                if isinstance(article, dict):
                    title = article.get("title", article.get("headline", "Untitled Article"))
                    url = article.get("url", article.get("link", "#"))
                    source = article.get("source", article.get("publisher", "Unknown"))
                    date = article.get("date", article.get("published_date", ""))
                    
                    with st.expander(f"{idx}. {title}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Source:** {source}")
                            if date:
                                st.markdown(f"**Date:** {date}")
                        with col2:
                            st.markdown(f"[Read Article]({url})")
                        
                        summary = article.get("summary", article.get("snippet", ""))
                        if summary:
                            st.markdown(f"**Summary:** {summary}")
                else:
                    st.markdown(f"{idx}. {article}")
        else:
            st.info("No news sources available")
    
    # Tab 3: Wikipedia
    with tab3:
        wiki_data = data.get("enrichments", {}).get("wikipedia", {})
        wiki_url = wiki_data.get("url", "")
        wiki_summary = wiki_data.get("summary", "")
        wiki_sections = wiki_data.get("sections", [])
        
        if wiki_url or wiki_summary:
            st.markdown("**Wikipedia Article**")
            if wiki_url:
                st.markdown(f"**URL:** [{wiki_url}]({wiki_url})")
            
            if wiki_summary:
                with st.expander("Article Summary", expanded=True):
                    st.markdown(wiki_summary)
            
            if wiki_sections:
                st.markdown(f"**{len(wiki_sections)} sections analyzed:**")
                for section in wiki_sections:
                    if isinstance(section, dict):
                        st.markdown(f"- {section.get('title', 'Untitled Section')}")
                    else:
                        st.markdown(f"- {section}")
        else:
            st.info("No Wikipedia data available")
    
    # Tab 4: DED & Official Sources
    with tab4:
        ded_data = data.get("enrichments", {}).get("ded", {})
        official_website = data.get("website", data.get("official_website", ""))
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🏛️ DED (Department of Economic Development)**")
            if ded_data:
                license_no = ded_data.get("license_number", "")
                trade_name = ded_data.get("trade_name", "")
                status = ded_data.get("status", "")
                
                if license_no:
                    st.markdown(f"**License Number:** {license_no}")
                if trade_name:
                    st.markdown(f"**Trade Name:** {trade_name}")
                if status:
                    st.markdown(f"**Status:** {status}")
                
                ded_url = ded_data.get("url", "https://www.ded.ae")
                st.markdown(f"[View on DED Portal]({ded_url})")
            else:
                st.info("No DED data available")
        
        with col2:
            st.markdown("**🌐 Official Website**")
            if official_website:
                st.markdown(f"[{official_website}]({official_website})")
                
                # Show if website was verified
                has_official = data.get("has_official_website", False)
                if has_official:
                    st.success("✓ Verified official website")
            else:
                st.info("No official website found")
        
        # Knowledge Graph data
        kg_data = data.get("knowledge_graph", {})
        if kg_data:
            st.markdown("---")
            st.markdown("**📊 Knowledge Graph Data**")
            with st.expander("View Knowledge Graph Information", expanded=False):
                for key, value in kg_data.items():
                    if value and key not in ['source', 'raw']:
                        st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
    
    # Summary statistics at the bottom
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        serp_count = len(data.get("serp_links", []))
        st.metric("SERP Links", serp_count)
    
    with col2:
        news_count = len(data.get("enrichments", {}).get("news", {}).get("sources", []))
        st.metric("News Articles", news_count)
    
    with col3:
        has_wiki = "✓" if data.get("enrichments", {}).get("wikipedia", {}).get("url") else "✗"
        st.metric("Wikipedia", has_wiki)
    
    with col4:
        has_ded = "✓" if data.get("enrichments", {}).get("ded", {}) else "✗"
        st.metric("DED Data", has_ded)
