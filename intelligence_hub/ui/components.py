import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import textwrap
import uuid
from intelligence_hub.ui.pipeline_viz import get_default_agent_status

logo_url = "https://www.emiratesnbd.com/-/media/enbd/images/logos/favicon.png"


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
                {"icon": "🕷️", "label": "Scraping"},
            ],
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
                parallel_html += "</div>"
                html += parallel_html
            html += "</div>"
        else:
            # Render Single Step
            pulse = "<div class='step-pulse'></div>" if status == "active" else ""
            sub_items = (
                f'<div class="step-subitems">{" • ".join(step["sub_items"])}</div>'
                if "sub_items" in step
                else ""
            )

            step_html = f'<div class="pipeline-step {status}">'
            step_html += f'<div class="step-indicator"><span class="step-icon">{step["icon"]}</span>{pulse}</div>'
            step_html += f'<div class="step-content"><span class="step-label">{step["label"]}</span>{sub_items}</div>'
            step_html += "</div>"
            html += step_html

        # Connector (if not last step)
        if i < len(steps) - 1:
            conn_status = "completed" if status == "completed" else "pending"
            html += f'<div class="pipeline-connector {conn_status}"></div>'

    html += "</div></div>"
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

            st.html(html)
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
    st.html(
        f"""<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px;">{make_metric_card("Revenue (Current)", curr.get("rev"), curr.get("trend"))}{make_metric_card("Revenue (Last Yr)", last_y.get("rev"), "Hist")}{make_metric_card("Net Profit (Current)", curr.get("profit"), "")}{make_metric_card("Net Profit (Last Yr)", last_y.get("profit"), "Hist")}</div>"""
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
    st.plotly_chart(fig, width="stretch", key="stock_performance_chart")


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
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔍 SERP Links", "📰 News Sources", "📖 Wikipedia", "🌐 DED & Official"]
    )

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
                    title = article.get(
                        "title", article.get("headline", "Untitled Article")
                    )
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
                    if value and key not in ["source", "raw"]:
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
        has_wiki = (
            "✓" if data.get("enrichments", {}).get("wikipedia", {}).get("url") else "✗"
        )
        st.metric("Wikipedia", has_wiki)

    with col4:
        has_ded = "✓" if data.get("enrichments", {}).get("ded", {}) else "✗"
        st.metric("DED Data", has_ded)


def render_top_news(data):
    """Renders top news articles in an attractive card layout"""

    # Extract news from different possible locations
    news_articles = []

    # Check enrichments.news.sources
    if data.get("enrichments", {}).get("news", {}).get("sources"):
        news_articles = data["enrichments"]["news"]["sources"]
    # Check news_articles directly
    elif data.get("news_articles"):
        news_articles = data["news_articles"]
    # Check enrichments.news directly
    elif data.get("enrichments", {}).get("news"):
        news_data = data["enrichments"]["news"]
        if isinstance(news_data, list):
            news_articles = news_data
        elif isinstance(news_data, dict) and news_data.get("articles"):
            news_articles = news_data["articles"]

    if not news_articles:
        st.info("📰 No recent news articles available")
        return

    # Display top 5 news articles
    top_news = news_articles[:5] if len(news_articles) > 5 else news_articles

    st.markdown(
        f"**{len(news_articles)} articles found** • Showing top {len(top_news)}"
    )

    for idx, article in enumerate(top_news, 1):
        # Handle different data structures
        if isinstance(article, dict):
            title = article.get("title", article.get("headline", "Untitled"))
            url = article.get("url", article.get("link", "#"))
            source = article.get("source", article.get("publisher", "Unknown Source"))
            date = article.get("date", article.get("published", ""))
            snippet = article.get("snippet", article.get("description", ""))
        else:
            # If article is a string or other format
            title = str(article)
            url = "#"
            source = "News Source"
            date = ""
            snippet = ""

        # Create news card
        with st.container():
            st.html(
                textwrap.dedent(
                    f"""
            <div style="
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.9) 100%);
                border-left: 4px solid #0077ff;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 2px 8px rgba(0, 51, 102, 0.08);
                transition: all 0.2s ease;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                    <span style="
                        background: linear-gradient(135deg, #003366 0%, #0077ff 100%);
                        color: white;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                    ">#{idx}</span>
                    <span style="color: #64748b; font-size: 12px;">{date}</span>
                </div>
                <h4 style="margin: 8px 0; color: #003366; font-size: 16px; font-weight: 600;">
                    <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">
                        {title}
                    </a>
                </h4>
                {f'<p style="color: #64748b; font-size: 14px; margin: 8px 0; line-height: 1.5;">{snippet[:150]}...</p>' if snippet else ''}
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 8px;">
                    <span style="color: #0077ff; font-size: 12px; font-weight: 600;">📰 {source}</span>
                    <a href="{url}" target="_blank" style="
                        color: #0077ff;
                        font-size: 12px;
                        text-decoration: none;
                        margin-left: auto;
                    ">Read more →</a>
                </div>
            </div>
            """
                )
            )


def render_company_summary_card(
    placeholder=None, key="btn_continue_investigation", show_button=True
):
    """
    Renders the premium summary card for the resolved company.
    This includes company description, key facts, stakeholders, and social links.
    """
    # Use placeholder if provided, else main flow
    context = placeholder.container() if placeholder else st.container()

    # Check if we should return early (user clicked Abort)
    if st.session_state.get("abort_investigation", False):
        return False

    with context:
        # Layout: Name Display (Full Width)
        col_display = st.container()

        with col_display:
            if st.session_state.get("is_resolving"):
                # Resolving state (Stay here until profiling finishes)
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
            elif st.session_state.get("canonical_name"):
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

        # Prepare Profile Data (Default: Not Available)
        desc = "No company profile data available yet. Start a search to generate insights."
        ticker = "N/A"
        exchange = ""
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
        ticker = ""
        exchange = ""

        # Override with real data if profile exists AND we aren't still resolving Phase 1
        if st.session_state.get("canonical_name") and not st.session_state.get(
            "is_resolving"
        ):
            profile = st.session_state.get("company_profile", {})

            # Override with real data
            desc = profile.get("description") or desc
            ticker = profile.get("ticker") or ticker
            exchange = profile.get("exchange") or exchange
            ticker_display = (
                f"{exchange}:{ticker}"
                if exchange
                else (ticker if ticker and ticker != "N/A" else "")
            )

            # Confidence Logic
            confidence = profile.get("confidence_score", 0)
            badge_html = ""
            if confidence > 0:
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
            kg_source = profile.get("knowledge_graph", {})
            if not isinstance(kg_source, dict):
                kg_source = {}

            kg_data = {}

            if kg_source.get("customer_service"):
                kg_data["Customer service"] = kg_source.get("customer_service")

            ceo = kg_source.get("ceo")
            founder = kg_source.get("founder")

            leadership_data = profile.get("leadership", [])

            if not ceo:
                if isinstance(leadership_data, dict):
                    for k, v in leadership_data.items():
                        if "ceo" in k.lower() or "chief executive" in k.lower():
                            ceo = v
                            break
                        if "ceo" in str(v).lower():
                            ceo = v
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

            if kg_source.get("founded"):
                kg_data["Founded"] = kg_source.get("founded")
            if kg_source.get("headquarters"):
                kg_data["Headquarters"] = kg_source.get("headquarters")
            if kg_source.get("hubs"):
                kg_data["Hubs"] = kg_source.get("hubs")
            if kg_source.get("parent_organization"):
                kg_data["Parent Org"] = kg_source.get("parent_organization")

            if "Founded" not in kg_data and profile.get("founded"):
                kg_data["Founded"] = profile.get("founded")
            if "Headquarters" not in kg_data and profile.get("headquarters"):
                kg_data["Headquarters"] = profile.get("headquarters")
            if "Type" not in kg_data and (kg_source.get("type") or profile.get("type")):
                kg_data["Type"] = kg_source.get("type") or profile.get("type")

            industry = profile.get("industry") or profile.get("sector")
            if industry:
                kg_data["Industry"] = industry

            ticker = profile.get("ticker")
            exchange = profile.get("exchange")
            if ticker and ticker != "N/A":
                kg_data["Stock"] = f"{exchange}:{ticker}" if exchange else ticker

            subs = kg_source.get("subsidiaries") or profile.get("subsidiaries")
            if subs:
                if isinstance(subs, list):
                    kg_data["Subsidiaries"] = ", ".join([str(s) for s in subs[:3]]) + (
                        "..." if len(subs) > 3 else ""
                    )
                else:
                    kg_data["Subsidiaries"] = str(subs)

            other_facts = kg_source.get("other_facts", {})
            if isinstance(other_facts, dict):
                for k, v in other_facts.items():
                    if k not in kg_data and v:
                        display_k = k.replace("_", " ").title()
                        if isinstance(v, list):
                            v = ", ".join([str(i) for i in v[:3]])
                        kg_data[display_k] = v

            if kg_data:
                rows = []
                for k, v in kg_data.items():
                    rows.append(
                        f"""
                     <div style="margin-bottom: 5px; font-size: 0.9rem; line-height: 1.5; color: #202124;">
                        <span style="font-weight: 700; color: #202124;">{k}:</span>
                        <span style="color: #4d5156;">{v}</span>
                     </div>
                     """
                    )
                kg_html = f'<div style="margin-top: 15px; margin-bottom: 20px;">{"".join(rows)}</div>'

            # Stakeholders & Shareholders
            leadership_names = []
            shareholders_names = []
            shareholders = profile.get("major_shareholders") or profile.get(
                "ownership_structure", {}
            ).get("major_shareholders", [])

            if isinstance(leadership_data, list):
                leadership_names.extend(
                    [
                        p if isinstance(p, str) else p.get("name", str(p))
                        for p in leadership_data[:4]
                    ]
                )
            elif isinstance(leadership_data, dict):
                l_keys = list(leadership_data.keys())
                for k in l_keys[:4]:
                    v = leadership_data[k]
                    if k.lower() in ["ceo", "founder", "chairman", "president"]:
                        leadership_names.append(v)
                    else:
                        leadership_names.append(f"{v}")

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
                    if len(k) > len(str(v)):
                        shareholders_names.append(f"{k} ({v})")
                    else:
                        shareholders_names.append(f"{v} ({k})")

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
                stakeholders_html = "".join(parts)

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

            social_html = ""
            socials = profile.get("social_media", {})
            if not isinstance(socials, dict):
                socials = {}
            socials = socials.copy()

            wiki_url = profile.get("wikipedia") or profile.get("wikipedia_url")
            if not wiki_url:
                kg_tmp = profile.get("knowledge_graph", {})
                if isinstance(kg_tmp, dict):
                    src = kg_tmp.get("source", {})
                    if src.get("name") and "wikipedia" in str(src.get("name")).lower():
                        wiki_url = src.get("link")

            if wiki_url:
                socials["Wikipedia"] = wiki_url

            if socials:
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
                    img_src = "https://img.icons8.com/color/48/globe--v1.png"
                    for skey, asset_url in icon_assets.items():
                        if skey in p_lower:
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

            refs = list(profile.get("references", []))
            organic = profile.get("organic_results", [])
            seen_urls = {r.get("url") or r.get("link") for r in refs}

            if organic and isinstance(organic, list):
                for res in organic[:5]:
                    link = res.get("link")
                    if link and link not in seen_urls:
                        raw_source = res.get("source") or res.get("title", "Link")
                        source_name = raw_source
                        if " - " in source_name:
                            source_name = source_name.split(" - ")[-1]

                        refs.append({"source": source_name[:20], "url": link})
                        seen_urls.add(link)

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
        if st.session_state.get("canonical_name"):
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

            # Continue/Abort Controls
            if (
                st.session_state.get("investigation_paused")
                and not st.session_state.get("analysis_complete")
                and show_button
            ):
                st.html('<div style="height:20px;"></div>')
                col_continue, col_abort = st.columns([2.5, 1])

                with col_continue:
                    btn_disabled = not st.session_state.get("canonical_name")
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
        elif st.session_state.get("is_resolving"):
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
