import streamlit as st
import plotly.graph_objects as go


def get_test_dashboard_data():
    """
    Returns comprehensive test data for dashboard preview.
    This data structure matches the expected format from the investigation pipeline.
    """
    return {
        "meta": {
            "name": "Emirates NBD Bank PJSC",
            "description": "Emirates NBD is a leading banking group in the Middle East, North Africa and Turkey (MENAT) region. The bank was formed in 2007 through the merger of Emirates Bank International and the National Bank of Dubai. Emirates NBD offers a comprehensive range of products and services including retail banking, corporate banking, Islamic banking, investment banking, private banking, asset management, global markets and treasury, and brokerage operations.",
            "website": "https://www.emiratesnbd.com",
            "founded": "2007",
            "headquarters": "Dubai, UAE",
            "sector": "Banking & Financial Services",
            "industry": "Banking",
            "exchange": "DFM",
            "ticker": "EMIRATESNBD",
        },
        "financials": {
            "current": {
                "period": "2025",
                "rev": "AED 25.4B",
                "profit": "AED 12.8B",
                "price": "AED 16.50",
                "trend": "+8.2%",
                "roe": "14.2%",
                "roa": "1.8%",
                "npl_ratio": "4.1%",
                "capital_adequacy": "18.5%",
                "cost_to_income": "32.7%",
                "liquidity_coverage_ratio": "165%",
            },
            "last_year": {"period": "2024", "rev": "AED 23.1B", "profit": "AED 11.5B"},
            "market_cap": "AED 68.5B",
        },
        "enrichments": {
            "news": {
                "sources": [
                    {
                        "title": "Gulf's Third Biggest Bank Leads Funding Round Into Property App",
                        "url": "https://www.bloomberg.com/news/articles/2026-02-17/gulf-s-third-biggest-bank-leads-funding-round",
                        "source": "Bloomberg",
                        "date": "Feb 17, 2026",
                    },
                    {
                        "title": "UAE's Emirates NBD Secures $3 Billion Stake in India's RBL Bank",
                        "url": "https://www.msn.com/en-us/money/companies/uae-emirates-nbd-secures",
                        "source": "MSN",
                        "date": "Feb 16, 2026",
                    },
                    {
                        "title": "Dubai Emirates NBD tightens price on 5-year €500mln green bond",
                        "url": "https://www.zawya.com/en/business/banking/dubai-emirates-nbd-tightens-price",
                        "source": "ZAWYA",
                        "date": "Feb 11, 2026",
                    },
                ]
            },
            "wikipedia": {"url": "https://en.wikipedia.org/wiki/Emirates_NBD"},
            "serp": {"count": 15},
            "ded": {
                "canonical_name": "Emirates NBD Bank PJSC",
                "query_type": "hybrid_search",
                "total_companies": 2,
                "companies": [
                    {
                        "trade_name_en": "EMIRATES NBD BANK PJSC",
                        "trade_name_ar": "",
                        "similarity_score": 0.97,
                        "match_type": "similarity",
                        "license_count": 3,
                        "license_numbers": [],
                        "license_categories": ["Commercial"],
                        "activities": ["Commercial Bank", "Investment Banking"],
                        "activity_count": 2,
                        "partners": [],
                        "partner_count": 0,
                        "commerce_register_numbers": [],
                        "issue_authorities": [],
                        "earliest_issue_date": "12/03/2007",
                        "latest_expiry_date": "31/12/2027",
                    },
                    {
                        "trade_name_en": "EMIRATES NBD CAPITAL (PJSC)",
                        "trade_name_ar": "",
                        "similarity_score": 0.61,
                        "match_type": "similarity",
                        "license_count": 1,
                        "license_numbers": [],
                        "license_categories": ["Professional"],
                        "activities": ["Financial Consultancy"],
                        "activity_count": 1,
                        "partners": [],
                        "partner_count": 0,
                        "commerce_register_numbers": [],
                        "issue_authorities": [],
                        "earliest_issue_date": "05/06/2010",
                        "latest_expiry_date": "30/06/2026",
                    },
                ],
                "summary": {
                    "overview": "Found 2 matching UAE company(ies) with 4 active license(s). Top match: EMIRATES NBD BANK PJSC (similarity: 97%, match type: similarity)",
                    "active_licenses": [],
                    "potential_sectors": ["Commercial", "Professional"],
                    "shareholder_details": [],
                    "subsidiary_info": [
                        {
                            "name": "EMIRATES NBD CAPITAL (PJSC)",
                            "relationship": "Potential subsidiary (name similarity)",
                            "licenses": 1,
                            "activities": ["Financial Consultancy"],
                        }
                    ],
                    "match_confidence": "very_high",
                    "total_companies_found": 2,
                    "total_licenses": 4,
                },
                "timestamp": "2026-02-25T00:00:00",
            },
        },
        "insights": [
            {
                "category": "Strategic Growth",
                "text": "Emirates NBD is actively expanding its regional footprint through strategic acquisitions, including the recent $3B stake in India's RBL Bank, positioning itself as a major player in South Asian markets.",
            },
            {
                "category": "Sustainability",
                "text": "The bank's €500M green bond issuance demonstrates strong commitment to sustainable finance and ESG principles, aligning with UAE's net-zero ambitions.",
            },
            {
                "category": "Digital Innovation",
                "text": "Leading funding rounds in proptech startups indicates the bank's focus on digital transformation and innovation in the real estate financing sector.",
            },
            {
                "category": "Financial Performance",
                "text": "Strong YoY revenue growth of 10% and profit increase of 11.3% reflect robust operational performance and effective risk management strategies.",
            },
            {
                "category": "Market Position",
                "text": "As the third-largest bank in the Gulf region with AED 68.5B market cap, Emirates NBD maintains a dominant position in the MENAT banking sector.",
            },
        ],
        "competitors": [
            {
                "Company": "First Abu Dhabi Bank",
                "Mkt Cap": "AED 112.5B",
                "P/E": "12.3",
                "Rev Growth": "+9.5%",
            },
            {
                "Company": "Abu Dhabi Commercial Bank",
                "Mkt Cap": "AED 45.2B",
                "P/E": "10.8",
                "Rev Growth": "+7.2%",
            },
            {
                "Company": "Dubai Islamic Bank",
                "Mkt Cap": "AED 38.7B",
                "P/E": "11.5",
                "Rev Growth": "+8.9%",
            },
            {
                "Company": "Mashreq Bank",
                "Mkt Cap": "AED 28.3B",
                "P/E": "9.7",
                "Rev Growth": "+6.4%",
            },
            {
                "Company": "Abu Dhabi Islamic Bank",
                "Mkt Cap": "AED 24.1B",
                "P/E": "10.2",
                "Rev Growth": "+5.8%",
            },
            {
                "Company": "RAK Bank",
                "Mkt Cap": "AED 6.8B",
                "P/E": "8.9",
                "Rev Growth": "+4.3%",
            },
        ],
        "logs": [
            "Starting enrichment for Emirates NBD Bank PJSC...",
            "Master Agent: Resolving canonical name...",
            "Master Agent completed successfully",
            "Wikipedia Agent: Fetching company information...",
            "Wikipedia Agent: success",
            "News Agent: Collecting latest news articles...",
            "News Agent: success",
            "DED Agent: Retrieving license information...",
            "DED Agent: success",
            "Scraper Orchestrator: Processing documents...",
            "Scraper Orchestrator completed",
            "Vectorizer Agent: Indexing documents...",
            "Vectorizer Agent completed",
            "PDF Agent: Analyzing financial statements...",
            "PDF Agent completed",
            "Analyst Agent: Generating insights...",
            "Analyst Agent: Generating insights...",
            "Analyst Agent completed successfully",
        ],
        "sources": [
            {
                "title": "Official Website",
                "url": "https://www.emiratesnbd.com",
                "type": "official",
            },
            {
                "title": "Wikipedia Profile",
                "url": "https://en.wikipedia.org/wiki/Emirates_NBD",
                "type": "reference",
            },
            {
                "title": "Bloomberg: Gulf Banking Funding",
                "url": "https://www.bloomberg.com/news/articles/2026-02-17/gulf-s-third-biggest-bank-leads-funding-round",
                "type": "news",
                "source": "Bloomberg",
            },
            {
                "title": "MSN: RBL Bank Stake",
                "url": "https://www.msn.com/en-us/money/companies/uae-emirates-nbd-secures",
                "type": "news",
                "source": "MSN",
            },
            {
                "title": "ZAWYA: Green Bond",
                "url": "https://www.zawya.com/en/business/banking/dubai-emirates-nbd-tightens-price",
                "type": "news",
                "source": "ZAWYA",
            },
            {
                "title": "DFM Listing Page",
                "url": "https://www.dfm.ae/en/issuers/listed-securities/securities-details?id=EMIRATESNBD",
                "type": "exchange",
            },
            {
                "title": "Annual Report 2025 (PDF)",
                "url": "https://www.emiratesnbd.com/-/media/enbd/files/annual-report-2025.pdf",
                "type": "pdf",
            },
        ],
    }


def render_main_dashboard(placeholder=None):
    """
    Renders an elegant, professional intelligence dashboard with premium styling.
    Each section updates independently as agents complete their tasks.
    """

    # Get data from session state
    data = st.session_state.get("data", {})

    if not data:
        st.info("📊 Dashboard will appear here once investigation completes...")
        return

    # Dashboard Header - Dark gradient matching main UI banner
    st.html(
        """
    <div style="
        background: linear-gradient(90deg, #003366 0%, #00509e 100%);
        border-radius: 12px;
        padding: 24px 36px;
        margin-top: 32px;
        margin-bottom: 32px;
        box-shadow: 0 10px 20px rgba(0, 48, 99, 0.35);
    ">
        <div style="
            font-family: 'Poppins', sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: white;
            margin-bottom: 6px;
            letter-spacing: 0.02em;
            text-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
        ">
            Profile Dashboard
        </div>
        <div style="
            font-family: 'Poppins', sans-serif;
            font-size: 14px;
            color: #e5eaf0;
            font-weight: 400;
            letter-spacing: 0.01em;
        ">
            Comprehensive financial analysis and strategic insights for relationship management
        </div>
    </div>
    """
    )

    # Extract data safely with fallbacks
    meta = data.get("meta", {})
    financials = data.get("financials", {})
    enrichments = data.get("enrichments", {})

    # === SECTION 1: KEY METRICS - Premium Card Design ===
    st.html(
        """
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 20px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #0077ff;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 24px;">📊</span>
        <span>Key Performance Indicators</span>
    </div>
    """
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        founded = meta.get("founded", "N/A")
        founding_year = None
        if founded and founded != "N/A":
            import re

            year_match = re.search(r"\b(1\d{3}|20\d{2})\b", str(founded))
            if year_match:
                founding_year = int(year_match.group(1))

        if founding_year:
            years = 2026 - founding_year
            st.metric("Years Operating", f"{years}", f"Since {founded}")
        elif founded and founded != "N/A":
            st.metric("Founded", founded)
        else:
            st.metric("Founded", "N/A")

    with col2:
        revenue = (
            financials.get("current", {}).get("rev", "N/A") if financials else "N/A"
        )
        trend = financials.get("current", {}).get("trend", None) if financials else None
        # Shorten revenue display
        if len(revenue) > 12:
            revenue = revenue[:12] + "..."
        st.metric("Revenue", revenue if revenue != "N/A" else "Pending", trend)

    with col3:
        hq = meta.get("headquarters", meta.get("hq", "N/A"))
        # Shorten HQ display
        if len(hq) > 15:
            hq = hq[:15] + "..."
        st.metric("Headquarters", hq if hq != "N/A" else "N/A")

    with col4:
        industry = meta.get("sector", meta.get("industry", "N/A"))
        # Shorten industry display
        if len(industry) > 20:
            industry = industry[:20] + "..."
        st.metric("Industry", industry if industry != "N/A" else "N/A")

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 2: COMPANY PROFILE - Full Width ===
    if meta:
        company_name = meta.get("name", "Unknown Company")
        description = meta.get("description", "No description available")
        website = meta.get("website", "#")

        # Get DED data (handle both raw and formatted keys)
        ded_data = enrichments.get("ded") or enrichments.get("uae_ded_license") or {}
        shareholder_data = (
            enrichments.get("shareholders")
            or enrichments.get("shareholder_structure")
            or {}
        )

        st.html(
            f"""
        <div style="
            font-family: 'Poppins', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: #003366;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #0077ff;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -0.3px;
        ">
            <span style="font-size: 24px;">🏢</span>
            <span>Company Profile</span>
        </div>
        """
        )

        st.html(
            f"""
        <div style="
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 4px 16px rgba(0, 51, 102, 0.08);
            margin-bottom: 32px;
        ">
            <h3 style="
                font-family: 'Poppins', sans-serif;
                color: #003366;
                margin: 0 0 16px 0;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: -0.3px;
            ">{company_name}</h3>
            <p style="
                font-family: 'Poppins', sans-serif;
                color: #475569;
                line-height: 1.7;
                margin-bottom: 20px;
                font-size: 14px;
                font-weight: 400;
            ">{description}</p>
            {f'<div style="margin-bottom: 16px;"><a href="{website}" target="_blank" style="font-family: Poppins, sans-serif; color: #0077ff; text-decoration: none; font-weight: 600; font-size: 14px;">🌐 Visit Website →</a></div>' if website != "#" else ''}
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: 24px; padding-top: 24px; border-top: 1px solid #e2e8f0;">
                <div>
                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Industry</div>
                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('sector', 'N/A')}</div>
                </div>
                <div>
                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Founded</div>
                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('founded', '—')}</div>
                </div>
                <div>
                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Headquarters</div>
                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 14px; font-weight: 600;">{meta.get('headquarters', '—')}</div>
                </div>
                <div>
                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Listing</div>
                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('exchange', 'Priv.')}{f": {meta.get('ticker')}" if meta.get('ticker') else ""}</div>
                </div>
            </div>
        </div>
        """
        )

        # === SHAREHOLDER STRUCTURE SECTION ===
        if shareholder_data:
            major_sh = shareholder_data.get("major_shareholders", [])
            ownership_type = shareholder_data.get("ownership_type", "N/A")
            ubo = shareholder_data.get("ultimate_beneficial_owner", "N/A")
            notes = shareholder_data.get("ownership_notes", "")

            if major_sh or notes or ownership_type != "N/A":
                st.html(
                    f"""
                <div style="
                    font-family: 'Poppins', sans-serif;
                    font-size: 20px;
                    font-weight: 700;
                    color: #003366;
                    margin-top: 32px;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 2px solid #0077ff;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    letter-spacing: -0.3px;
                ">
                    <span style="font-size: 24px;">👥</span>
                    <span>Ownership & Shareholder Structure</span>
                </div>
                """
                )

                # Top Stats Row: Ownership Type & UBO
                st.html(
                    f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;">
                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0, 51, 102, 0.04);">
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Ownership Type</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #003366; font-size: 18px; font-weight: 700;">{ownership_type}</div>
                    </div>
                    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0, 51, 102, 0.04);">
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Ultimate Beneficial Owner (UBO)</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #003366; font-size: 18px; font-weight: 700;">{ubo if ubo else 'Not Disclosed'}</div>
                    </div>
                </div>
                """
                )

                # Main Content: Visualization and Detailed Cards
                col_chart, col_sh_details = st.columns([1, 1.2])

                with col_chart:
                    # Parse percentages for Plotly Pie Chart
                    labels = []
                    values = []
                    total_p = 0
                    for s in major_sh:
                        try:
                            p_val = s.get("percentage", "0")
                            if p_val and isinstance(p_val, str):
                                p_val = p_val.replace("%", "").strip()
                                if p_val and p_val != "N/A":
                                    p = float(p_val)
                                    labels.append(s.get("name", "Unknown"))
                                    values.append(p)
                                    total_p += p
                        except:
                            pass

                    if values:
                        if total_p < 99.0:
                            labels.append("Others/Minority")
                            values.append(max(0, 100 - total_p))

                        fig = go.Figure(
                            data=[
                                go.Pie(
                                    labels=labels,
                                    values=values,
                                    hole=0.5,
                                    marker=dict(
                                        colors=[
                                            "#003366",
                                            "#0077ff",
                                            "#3b82f6",
                                            "#60a5fa",
                                            "#93c5fd",
                                            "#bfdbfe",
                                            "#f1f5f9",
                                        ]
                                    ),
                                    textinfo="percent",
                                    hoverinfo="label+percent",
                                    insidetextorientation="radial",
                                )
                            ]
                        )
                        fig.update_layout(
                            margin=dict(t=0, b=0, l=0, r=0),
                            showlegend=True,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=-0.2,
                                xanchor="center",
                                x=0.5,
                            ),
                            height=350,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="Poppins, sans-serif", size=10),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.html(
                            f"""
                        <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 12px; height: 350px; display: flex; align-items: center; justify-content: center; flex-direction: column; color: #64748b;">
                            <span style="font-size: 32px; margin-bottom: 12px;">📊</span>
                            <div style="font-family: 'Poppins', sans-serif; font-size: 13px;">No percentage data for visualization</div>
                        </div>
                        """
                        )

                with col_sh_details:
                    sh_cards_inner = "".join(
                        [
                            f"""
                        <div style="
                            background: white; 
                            border: 1px solid #e2e8f0; 
                            border-radius: 10px; 
                            padding: 14px 18px; 
                            margin-bottom: 12px; 
                            display: flex; 
                            justify-content: space-between; 
                            align-items: center; 
                            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
                        ">
                            <div style="flex: 1;">
                                <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 14px; font-weight: 700; margin-bottom: 2px;">{s.get('name', 'Unknown')}</div>
                                <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.3px;">{s.get('type', 'Entity')}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-family: 'Poppins', sans-serif; color: #0077ff; font-size: 16px; font-weight: 700;">{s.get('percentage') if s.get('percentage') else 'N/A'}</div>
                            </div>
                        </div>
                    """
                            for s in major_sh[:6]
                        ]
                    )

                    st.html(
                        f"""
                    <div style="max-height: 350px; overflow-y: auto; padding: 4px; padding-right: 8px;">
                        {sh_cards_inner if sh_cards_inner else '<div style="color: #64748b; font-family: Poppins, sans-serif; font-size: 13px; font-style: italic;">No major shareholders listed</div>'}
                    </div>
                    """
                    )

                if notes:
                    st.html(
                        f"""
                    <div style="
                        background: #f0f7ff; 
                        border-left: 4px solid #0077ff; 
                        padding: 18px 22px; 
                        border-radius: 4px 12px 12px 4px; 
                        margin-top: 24px;
                        box-shadow: 0 2px 8px rgba(0, 119, 255, 0.05);
                    ">
                        <div style="font-family: 'Poppins', sans-serif; color: #003366; font-size: 11px; font-weight: 800; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.6px;">Ownership & Governance Notes</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #334155; font-size: 14px; line-height: 1.6; font-weight: 400;">{notes}</div>
                    </div>
                    """
                    )

        # === DED LICENSE REGISTRY SECTION (Aggregated Format) ===
        if isinstance(ded_data, dict) and ded_data.get("companies"):
            companies_list = ded_data.get("companies", [])
            summary = ded_data.get("summary", {})
            match_confidence = summary.get("match_confidence", "unknown")
            potential_sectors = summary.get("potential_sectors", [])
            subsidiary_info = summary.get("subsidiary_info", [])

            conf_map = {
                "very_high": ("#003366", "#e0f2fe", "\u2705 Very High Confidence"),
                "high": ("#00509e", "#e0f2fe", "\u2705 High Confidence"),
                "medium": ("#0077ff", "#f0f9ff", "\u26a0\ufe0f Medium Confidence"),
                "low": ("#ef4444", "#fee2e2", "\u26a0\ufe0f Low Confidence"),
            }
            conf_color, conf_bg, conf_label = conf_map.get(
                match_confidence,
                ("#64748b", "#f1f5f9", "\u2139\ufe0f Confidence Unknown"),
            )

            # Section header
            st.html(
                f"""
            <div style="font-family:'Poppins',sans-serif; font-size:20px; font-weight:700;
                        color:#003366; margin-top:8px; margin-bottom:16px; padding-bottom:10px;
                        border-bottom:2px solid #0077ff; display:flex; align-items:center; gap:12px;">
                <span style="font-size:24px;">\U0001f3db\ufe0f</span>
                <span>DED License Registry</span>
                <span style="margin-left:auto; background:{conf_bg}; color:{conf_color};
                             font-size:11px; font-weight:700; padding:4px 12px; border-radius:20px;
                             border:1px solid {conf_color}33; text-transform:uppercase; letter-spacing:0.5px;">
                    {conf_label}
                </span>
            </div>
            """
            )

            # Top company match — compact detailed card
            if companies_list:
                top = companies_list[0]
                trade_name = top.get("trade_name_en", "Unknown Entity")
                similarity = top.get("similarity_score", 0)
                sim_pct = int(similarity * 100)
                lic_count = top.get("license_count", 0)
                categories = top.get("license_categories", [])
                activities = top.get("activities", [])
                license_nums = top.get("license_numbers", [])
                sector_tags = top.get("sector_tags", [])
                earliest = top.get("earliest_issue_date", "—")
                latest_exp = top.get("latest_expiry_date", "—")

                # Sector Tags (Blue shaded)
                sec_pills = "".join(
                    [
                        f'<span style="background:#003366;color:white;font-size:10px;font-weight:600;'
                        f'padding:4px 12px;border-radius:20px;white-space:nowrap;border:1px solid #002244;margin-bottom:4px;">{s}</span>'
                        for s in sector_tags[:6]
                    ]
                )

                # License Numbers (Numbered chips, Blue shades)
                lic_chips = "".join(
                    [
                        f'<span style="background:#f0f9ff;color:#0077ff;font-size:10px;font-weight:700;'
                        f'padding:4px 10px;border-radius:20px;border:1px solid #bae6fd;margin-bottom:4px;display:flex;align-items:center;gap:4px;">'
                        f'<span style="color:#003366;opacity:0.6;">#</span>{l}</span>'
                        for l in license_nums[:5]
                    ]
                )

                # Category & Activity (Light Blue shades)
                cat_pills = "".join(
                    [
                        f'<span style="background:#e0f2fe;color:#003366;font-size:10px;font-weight:600;'
                        f'padding:4px 10px;border-radius:20px;white-space:nowrap;border:1px solid #bae6fd;margin-bottom:4px;">{c}</span>'
                        for c in categories
                    ]
                )
                act_pills = "".join(
                    [
                        f'<span style="background:#f8fafc;color:#475569;font-size:10px;font-weight:600;'
                        f'padding:4px 10px;border-radius:20px;white-space:nowrap;border:1px solid #e2e8f0;margin-bottom:4px;">{a}</span>'
                        for a in activities[:6]
                    ]
                )

                st.html(
                    f"""
                <div style="width:560px; max-width:100%; font-family:'Poppins',sans-serif;">
                <div style="background:white; border:1px solid #e2e8f0; border-top:4px solid #003366; border-radius:14px;
                            padding:28px; box-shadow:0 8px 30px rgba(0,51,102,0.06); margin-bottom:24px;">

                    <!-- Header -->
                    <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:24px;">
                        <div style="flex:1;">
                            <div style="font-size:11px; font-weight:700; color:#0077ff; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;">✓ Primary Registration</div>
                            <div style="font-size:22px; font-weight:700; color:#003366; line-height:1.2;">{trade_name}</div>
                        </div>
                        <div style="text-align:center; background:#f0f9ff; border-radius:12px; padding:12px 18px; border:1px solid #bae6fd;">
                            <div style="color:#0077ff; font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">Match</div>
                            <div style="color:#003366; font-size:24px; font-weight:800; line-height:1;">{sim_pct}%</div>
                        </div>
                    </div>

                    <!-- Core Stats Grid -->
                    <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:24px;
                                padding:20px; background:#f8fafc; border-radius:12px;">
                        <div style="text-align:center;">
                            <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Licenses</div>
                            <div style="color:#003366; font-size:28px; font-weight:800;">{lic_count}</div>
                        </div>
                        <div style="text-align:center; border-left:1px solid #e2e8f0; border-right:1px solid #e2e8f0;">
                            <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">Established</div>
                            <div style="color:#1e293b; font-size:14px; font-weight:700;">{earliest}</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">License Expiry</div>
                            <div style="color:#1e293b; font-size:14px; font-weight:700;">{latest_exp}</div>
                        </div>
                    </div>

                    <!-- Sector Tags (Added) -->
                    {f'''<div style="margin-bottom:20px;">
                        <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; margin-bottom:8px; display:flex; align-items:center; gap:6px;">⌛ Entity Classification</div>
                        <div style="display:flex; flex-wrap:wrap; gap:8px;">{sec_pills}</div>
                    </div>''' if sec_pills else ''}

                    <!-- Licence Numbers -->
                    {f'''<div style="margin-bottom:20px;">
                        <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; margin-bottom:8px; display:flex; align-items:center; gap:6px;">📋 Licence Numbers</div>
                        <div style="display:flex; flex-wrap:wrap; gap:8px;">{lic_chips}</div>
                    </div>''' if lic_chips else ''}

                    <!-- License Types & Activities -->
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; padding-top:20px; border-top:1px solid #f1f5f9;">
                        {f'''<div>
                            <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; margin-bottom:10px;">License Type</div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px;">{cat_pills}</div>
                        </div>''' if cat_pills else ''}
                        {f'''<div>
                            <div style="color:#64748b; font-size:10px; font-weight:700; text-transform:uppercase; margin-bottom:10px;">Primary Activities</div>
                            <div style="display:flex; flex-wrap:wrap; gap:6px;">{act_pills}</div>
                        </div>''' if act_pills else ''}
                    </div>

                </div>
                </div>
                """
                )

            # Related Entities
            if subsidiary_info:
                sub_rows = "".join(
                    [
                        f'<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #f1f5f9;">'
                        f'<div><div style="font-family:Poppins,sans-serif;color:#1e293b;font-size:12px;font-weight:600;">{sub.get("name","—")}</div>'
                        f'<div style="font-family:Poppins,sans-serif;color:#64748b;font-size:10px;margin-top:2px;">{sub.get("relationship","")}</div></div>'
                        f'<div style="font-family:Poppins,sans-serif;color:#0077ff;font-size:12px;font-weight:700;white-space:nowrap;margin-left:12px;">{sub.get("licenses",0)} lic.</div></div>'
                        for sub in subsidiary_info[:4]
                    ]
                )
                st.html(
                    f"""
                <div style="width:560px; max-width:100%; background:white; border:1px solid #e2e8f0; border-radius:12px; padding:20px; box-shadow:0 4px 12px rgba(0,0,0,0.03);">
                    <div style="font-family:'Poppins',sans-serif;color:#003366;font-size:12px;font-weight:700;
                                text-transform:uppercase;letter-spacing:0.8px;margin-bottom:12px;display:flex;align-items:center;gap:8px;">\U0001f517 Related Network</div>
                    {sub_rows}
                </div>
                """
                )
    else:
        st.info("Company profile data pending...")

    # === SECTION 3: FINANCIAL SNAPSHOT ===
    curr = financials.get("current", {})
    period_label = curr.get("period", "")

    st.html(
        f"""
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 20px;
        font-weight: 700;
        color: #003366;
        margin-top: 32px;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid #0077ff;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 24px;">💰</span>
        <span>Financial Snapshot</span>
        {f'<span style="padding:5px; background: #e2e8f0; color: #475569; font-size: 11px; padding: 4px 12px; border-radius: 20px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border: 2px solid black;">{period_label}</span>' if period_label else ''}
    </div>
    """
    )

    if financials and "current" in financials:
        curr = financials.get("current", {})

        # Primary Metrics - 5 Big Cards in a Grid
        st.html(
            f"""
        <div style="
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 16px rgba(30, 58, 138, 0.3);
            color: white;
        ">
            <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px;">
                <div style="border-right: 1px solid rgba(255,255,255,0.2); padding-right: 15px;">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Total Revenue</div>
                    <div style="font-family: 'Poppins', sans-serif; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("rev", "N/A")}</div>
                </div>
                <div style="border-right: 1px solid rgba(255,255,255,0.2); padding-right: 15px;">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Net Profit</div>
                    <div style="font-family: 'Poppins', sans-serif; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("profit", "N/A")}</div>
                </div>
                <div style="border-right: 1px solid rgba(255,255,255,0.2); padding-right: 15px;">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Total Assets</div>
                    <div style="font-family: 'Poppins', sans-serif; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("assets", "N/A")}</div>
                </div>
                <div style="border-right: 1px solid rgba(255,255,255,0.2); padding-right: 15px;">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Total Liabilities</div>
                    <div style="font-family: 'Poppins', sans-serif; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("liabilities", "N/A")}</div>
                </div>
                <div>
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Total Equity</div>
                    <div style="font-family: 'Poppins', sans-serif; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("equity", "N/A")}</div>
                </div>
            </div>
        </div>
        """
        )

        # Key Banking Ratios - 4 cards in a grid
        metrics = [
            (
                "ROE",
                curr.get("roe", "N/A"),
                "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)",
            ),
            (
                "NPM",
                curr.get("npm", "N/A"),
                "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)",
            ),
            (
                "NIM",
                curr.get("nim", "N/A"),
                "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)",
            ),
            (
                "Cost-to-Income",
                curr.get("cost_to_income", "N/A"),
                "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)",
            ),
        ]

        st.html(
            f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;">
            {''.join([f'''
            <div style="
                background: {bg};
                border-radius: 10px;
                padding: 16px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                text-align: center;
            ">
                <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.9); font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">{label}</div>
                <div style="font-family: 'Poppins', sans-serif; color: white; font-size: 20px; font-weight: 800;">{val}</div>
            </div>
            ''' for label, val, bg in metrics])}
        </div>
        """
        )
    else:
        st.info("Financial data pending...")

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 4: LATEST NEWS - Enhanced Card Design ===
    st.html(
        """
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 3px solid #0077ff;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 28px;">📰</span>
        <span>Latest News & Market Updates</span>
    </div>
    """
    )

    # Check for news in multiple locations
    # News agent returns: {"articles": [...], "total_articles": N}
    news_data = enrichments.get("news", {})
    news_articles = []
    news_summary = ""

    # Robust extraction from various common formats
    if isinstance(news_data, dict):
        news_articles = news_data.get("sources") or news_data.get("articles") or []
        news_summary = news_data.get("summary", "")
    elif isinstance(news_data, list):
        news_articles = news_data

    # Fallbacks for articles if primary extraction failed
    if not news_articles:
        news_articles = data.get("news_articles", []) or data.get("news", [])

    if news_summary:
        # Convert simple markdown for HTML display
        processed_summary = news_summary.replace("**", "<b>", 1).replace(
            "**", "</b>", 1
        )
        # Handle multiple boldings
        while "**" in processed_summary:
            processed_summary = processed_summary.replace("**", "<b>", 1).replace(
                "**", "</b>", 1
            )

        # Convert simple dashes to styled list items
        lines = processed_summary.split("\n")
        html_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("-"):
                content = line[1:].strip()
                html_lines.append(
                    f'<div style="margin-bottom: 8px; display: flex; gap: 8px; align-items: flex-start;">'
                    f'<span style="color: #0077ff; font-weight: 900; margin-top: 1px;">•</span>'
                    f"<span>{content}</span></div>"
                )
            elif line:
                html_lines.append(f'<div style="margin-bottom: 8px;">{line}</div>')

        final_summary_html = "".join(html_lines)

        st.html(
            f"""
        <div style="
            background: rgba(0, 119, 255, 0.05);
            border-left: 4px solid #0077ff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            font-family: 'Poppins', sans-serif;
            color: #1e293b;
            line-height: 1.6;
            font-size: 15px;
        ">
            <div style="font-weight: 700; color: #003366; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">🤖</span> 
                <span>AI Insights Summary</span>
            </div>
            <div style="font-size: 14px;">
                {final_summary_html}
            </div>
        </div>
        """
        )

    if news_articles and len(news_articles) > 0:
        # Display top 3 news in a grid
        news_cols = st.columns(3)
        for idx, article in enumerate(news_articles[:3]):
            if isinstance(article, dict):
                title = article.get("title", "Untitled")
                # Support both 'url' (legacy) and 'link' (news agent)
                url = article.get("url") or article.get("link", "#")
                source = article.get("source", "News Source")
                # Support both 'date' (legacy) and 'published' (news agent)
                date = article.get("date") or article.get("published", "")
                # Trim RFC date to just the date part if needed (e.g. "Fri, 13 Feb 2026 04:50:22 GMT" -> "13 Feb 2026")
                if date and "," in date:
                    date = date.split(",")[1].strip().rsplit(" ", 1)[0].strip()

                with news_cols[idx]:
                    st.html(
                        f"""
                    <div style="
                        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                        border: 1px solid #e2e8f0;
                        border-left: 4px solid #0077ff;
                        border-radius: 12px;
                        padding: 20px;
                        height: 200px;
                        box-shadow: 0 4px 12px rgba(0, 51, 102, 0.08);
                        transition: all 0.3s ease;
                        cursor: pointer;
                    " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 24px rgba(0, 119, 255, 0.15)';" 
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0, 51, 102, 0.08)';">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                            <span style="
                                font-family: 'Poppins', sans-serif;
                                background: linear-gradient(135deg, #003366 0%, #0077ff 100%);
                                color: white;
                                padding: 4px 12px;
                                border-radius: 20px;
                                font-size: 10px;
                                font-weight: 700;
                                text-transform: uppercase;
                                letter-spacing: 0.5px;
                            ">{source}</span>
                            <span style="font-family: 'Poppins', sans-serif; color: #94a3b8; font-size: 11px; font-weight: 600;">{date}</span>
                        </div>
                        <h4 style="
                            font-family: 'Poppins', sans-serif;
                            margin: 0 0 12px 0;
                            color: #1e293b;
                            font-size: 14px;
                            font-weight: 700;
                            line-height: 1.4;
                            height: 80px;
                            overflow: hidden;
                            display: -webkit-box;
                            -webkit-line-clamp: 4;
                            -webkit-box-orient: vertical;
                            letter-spacing: -0.2px;
                        ">
                            <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">
                                {title}
                            </a>
                        </h4>
                        <a href="{url}" target="_blank" style="
                            font-family: 'Poppins', sans-serif;
                            color: #0077ff;
                            font-size: 12px;
                            font-weight: 600;
                            text-decoration: none;
                            display: inline-flex;
                            align-items: center;
                            gap: 4px;
                        ">
                            Read Full Article →
                        </a>
                    </div>
                    """
                    )
    else:
        st.info("📰 No recent news articles available")

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 5: STOCK PERFORMANCE - Chart Placeholder ===
    st.html(
        """
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 3px solid #0077ff;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 28px;">📈</span>
        <span>Stock Performance</span>
    </div>
    """
    )

    # Real stock chart
    chart_data = data.get("chart", {})
    if chart_data and "dates" in chart_data:
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
                    name="Price",
                )
            ]
        )

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=450,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="white",
            paper_bgcolor="white",
            hovermode="x unified",
            xaxis=dict(
                showgrid=True,
                gridcolor="#f1f5f9",
                tickfont=dict(color="#64748b", size=11),
                type="date",  # Changed from 'category' to 'date'
                rangeslider=dict(visible=False),
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#f1f5f9",
                tickfont=dict(color="#64748b", size=11),
                side="right",
            ),
        )

        fig.update_xaxes(
            dtick=7 * 24 * 60 * 60 * 1000,  # Every 7 days
            tickformat="%d\n%b-%y",  # Day on top, Month-Year below
            gridcolor="#f1f5f9",
            tickfont=dict(size=10, color="#64748b"),
        )

        # Add volume if available
        if "volume" in chart_data:
            fig.add_trace(
                go.Bar(
                    x=chart_data["dates"],
                    y=chart_data["volume"],
                    name="Volume",
                    marker_color="rgba(0, 51, 102, 0.1)",
                    yaxis="y2",
                )
            )
            fig.update_layout(
                yaxis2=dict(
                    title="Volume",
                    overlaying="y",
                    side="left",
                    showgrid=False,
                    tickfont=dict(color="#94a3b8", size=10),
                )
            )

        st.plotly_chart(fig, width="stretch", key="dashboard_stock_performance")
    else:
        # Fallback to placeholder if no data
        st.html(
            """
        <div style="
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 60px 40px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0, 51, 102, 0.08);
        ">
            <div style="
                font-family: 'Poppins', sans-serif;
                font-size: 48px;
                margin-bottom: 16px;
                opacity: 0.3;
            ">📊</div>
            <div style="
                font-family: 'Poppins', sans-serif;
                color: #64748b;
                font-size: 16px;
                font-weight: 500;
            ">Stock performance data currently unavailable</div>
            <div style="
                font-family: 'Poppins', sans-serif;
                color: #94a3b8;
                font-size: 13px;
                margin-top: 8px;
            ">Historical price data and terminal stats will appear here shortly</div>
        </div>
        """
        )

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 6: KEY COMPETITORS - Card Grid ===
    st.html(
        """
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 3px solid #0077ff;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 28px;">⚔️</span>
        <span>Key Competitors & Market Position</span>
    </div>
    """
    )

    # Get competitors data
    competitors = data.get("competitors", [])

    if competitors and len(competitors) > 0:
        # Display competitors in a 3-column grid
        comp_cols = st.columns(3)
        for idx, comp in enumerate(competitors[:6]):  # Show max 6 competitors
            if isinstance(comp, dict):
                company_name = comp.get("Company", "Unknown")
                mkt_cap = comp.get("Mkt Cap", "N/A")
                pe_ratio = comp.get("P/E", "N/A")
                rev_growth = comp.get("Rev Growth", "N/A")

                with comp_cols[idx % 3]:
                    st.html(
                        f"""
                    <div style="
                        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                        border: 1px solid #e2e8f0;
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 16px;
                        box-shadow: 0 2px 8px rgba(0, 51, 102, 0.06);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 6px 16px rgba(0, 119, 255, 0.12)';" 
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0, 51, 102, 0.06)';">
                        <h4 style="
                            font-family: 'Poppins', sans-serif;
                            color: #003366;
                            font-size: 16px;
                            font-weight: 700;
                            margin: 0 0 16px 0;
                            letter-spacing: -0.2px;
                        ">{company_name}</h4>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div style="
                                    font-family: 'Poppins', sans-serif;
                                    color: #64748b;
                                    font-size: 10px;
                                    font-weight: 700;
                                    text-transform: uppercase;
                                    margin-bottom: 4px;
                                    letter-spacing: 0.5px;
                                ">Market Cap</div>
                                <div style="
                                    font-family: 'Poppins', sans-serif;
                                    color: #1e293b;
                                    font-size: 14px;
                                    font-weight: 600;
                                ">{mkt_cap}</div>
                            </div>
                            <div>
                                <div style="
                                    font-family: 'Poppins', sans-serif;
                                    color: #64748b;
                                    font-size: 10px;
                                    font-weight: 700;
                                    text-transform: uppercase;
                                    margin-bottom: 4px;
                                    letter-spacing: 0.5px;
                                ">P/E Ratio</div>
                                <div style="
                                    font-family: 'Poppins', sans-serif;
                                    color: #1e293b;
                                    font-size: 14px;
                                    font-weight: 600;
                                ">{pe_ratio}</div>
                            </div>
                        </div>
                        
                        <div style="
                            margin-top: 12px;
                            padding-top: 12px;
                            border-top: 1px solid #e2e8f0;
                        ">
                            <div style="
                                font-family: 'Poppins', sans-serif;
                                color: #64748b;
                                font-size: 10px;
                                font-weight: 700;
                                text-transform: uppercase;
                                margin-bottom: 4px;
                                letter-spacing: 0.5px;
                            ">Revenue Growth</div>
                            <div style="
                                font-family: 'Poppins', sans-serif;
                                color: #0077ff;
                                font-size: 15px;
                                font-weight: 700;
                            ">{rev_growth}</div>
                        </div>
                    </div>
                    """
                    )
    else:
        st.info("⚔️ Competitor analysis data will appear here once available")

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 7: STRATEGIC INSIGHTS - Premium Cards ===
    st.html(
        """
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 3px solid #0077ff;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 28px;">💡</span>
        <span>Strategic Insights & RM Summary</span>
    </div>
    """
    )

    insights = data.get("insights", [])
    if insights and len(insights) > 0:
        # Display insights in 2 columns
        insight_cols = st.columns(2)
        for idx, insight in enumerate(insights[:6]):
            if isinstance(insight, dict):
                category = insight.get("category", "General")

                # Support both the rich schema (finding/trigger/action/source)
                # and the collapsed schema (text / insight) from legacy paths
                finding = insight.get("finding", "")
                trigger = insight.get("trigger", "")
                action = insight.get("action", "")
                source = insight.get("source", "")
                # Fallback: if none of the rich keys exist, use text/insight
                text_fallback = insight.get("text", insight.get("insight", ""))

                # Pick colour accent by category keyword
                accent = "#0077ff"
                if "lend" in category.lower():
                    accent = "#10b981"
                elif "trade" in category.lower():
                    accent = "#f59e0b"
                elif "kyc" in category.lower() or "compliance" in category.lower():
                    accent = "#ef4444"
                elif "operational" in category.lower():
                    accent = "#8b5cf6"

                # Build the inner body dynamically
                if finding or trigger or action:
                    body_html = f"""
                        {'<div style="margin-bottom:8px;"><span style="font-family:Poppins,sans-serif;font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">📍 Finding</span><div style="font-family:Poppins,sans-serif;color:#1e293b;font-size:13px;line-height:1.5;margin-top:2px;">' + finding + '</div></div>' if finding else ''}
                        {'<div style="margin-bottom:8px;"><span style="font-family:Poppins,sans-serif;font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">⚡ Trigger</span><div style="font-family:Poppins,sans-serif;color:#1e293b;font-size:13px;line-height:1.5;margin-top:2px;">' + trigger + '</div></div>' if trigger else ''}
                        {'<div style="background:rgba(0,119,255,0.06);border-radius:8px;padding:10px 12px;margin-top:10px;"><span style="font-family:Poppins,sans-serif;font-size:10px;font-weight:700;color:' + accent + ';text-transform:uppercase;letter-spacing:0.5px;">💡 RM Action</span><div style="font-family:Poppins,sans-serif;color:#0f172a;font-size:13px;font-weight:600;line-height:1.5;margin-top:4px;">' + action + '</div></div>' if action else ''}
                        {'<div style="margin-top:8px;font-family:Poppins,sans-serif;font-size:11px;color:#94a3b8;">Source: ' + source + '</div>' if source else ''}
                    """
                else:
                    body_html = f'<div style="font-family:Poppins,sans-serif;color:#334155;font-size:13px;line-height:1.6;">{text_fallback}</div>'

                with insight_cols[idx % 2]:
                    st.html(
                        f"""
                    <div style="
                        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                        border-left: 4px solid {accent};
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 16px;
                        box-shadow: 0 2px 8px rgba(0, 51, 102, 0.06);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateX(4px)'; this.style.boxShadow='0 4px 16px rgba(0, 119, 255, 0.12)';" 
                       onmouseout="this.style.transform='translateX(0)'; this.style.boxShadow='0 2px 8px rgba(0, 51, 102, 0.06)';">
                        <div style="
                            font-family: 'Poppins', sans-serif;
                            color: {accent};
                            font-weight: 700;
                            font-size: 11px;
                            text-transform: uppercase;
                            margin-bottom: 12px;
                            letter-spacing: 0.8px;
                        ">{category}</div>
                        {body_html}
                    </div>
                    """
                    )
            elif isinstance(insight, str):
                with insight_cols[idx % 2]:
                    st.markdown(f"• {insight}")
    else:
        st.info("Strategic insights will appear here once analysis completes...")

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 8: KEY RISKS & CONSIDERATIONS - Premium Cards ===
    st.html(
        """
    <div style="
        font-family: 'Poppins', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 24px;
        padding-bottom: 12px;
        border-bottom: 3px solid #ef4444;
        display: flex;
        align-items: center;
        gap: 12px;
        letter-spacing: -0.3px;
    ">
        <span style="font-size: 28px;">⚠️</span>
        <span>Key Risks & Considerations</span>
    </div>
    """
    )

    risks = data.get("risks", [])
    if risks and len(risks) > 0:
        # Display risks in 2 columns
        risk_cols = st.columns(2)
        for idx, item in enumerate(risks[:6]):
            if isinstance(item, dict):
                risk_title = item.get("risk", "Risk Factor")
                consideration = item.get("consideration", "No details available.")

                with risk_cols[idx % 2]:
                    st.html(
                        f"""
                    <div style="
                        background: linear-gradient(135deg, #fff5f5 0%, #fee2e2 100%);
                        border-left: 4px solid #ef4444;
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 16px;
                        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.06);
                    ">
                        <div style="
                            font-family: 'Poppins', sans-serif;
                            color: #ef4444;
                            font-weight: 700;
                            font-size: 11px;
                            text-transform: uppercase;
                            margin-bottom: 10px;
                            letter-spacing: 0.8px;
                        ">{risk_title}</div>
                        <div style="
                            font-family: 'Poppins', sans-serif;
                            color: #334155;
                            line-height: 1.6;
                            font-size: 14px;
                            font-weight: 400;
                        ">{consideration}</div>
                    </div>
                    """
                    )
    else:
        st.info(
            "Key risks and considerations will appear here once analysis completes..."
        )

    st.html("<div style='margin: 40px 0;'></div>")

    # === SECTION 8: DATA SOURCES & REFERENCES - Elegant Footer ===
    all_sources = data.get("sources", [])

    # Categorize and build the sources HTML first
    source_items_html = ""
    if all_sources:
        type_icons = {
            "official": "🌐",
            "reference": "📖",
            "news": "📰",
            "pdf": "📄",
            "disclosure": "📄",
            "exchange": "🏛️",
        }

        source_items_html = '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">'
        for src in all_sources:
            icon = type_icons.get(src.get("type", ""), "🔗")
            title = src.get("title", "Reference Link")
            url = src.get("url", "#")
            source_name = src.get("source", "")
            source_tag = (
                f'<span style="font-size: 10px; color: #64748b; margin-left: 4px;">({source_name})</span>'
                if source_name
                else ""
            )

            source_items_html += f"""
            <a href="{url}" target="_blank" style="
                text-decoration: none;
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 12px;
                display: flex;
                align-items: center;
                gap: 12px;
                transition: all 0.2s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            ">
                <span style="font-size: 18px;">{icon}</span>
                <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 13px; font-weight: 600;">{title}</div>
                    <div style="font-family: 'Poppins', sans-serif; color: #0077ff; font-size: 11px;">{url[:40]}{'...' if len(url) > 40 else ''} {source_tag}</div>
                </div>
            </a>
            """
        source_items_html += "</div>"
    else:
        source_items_html = """
        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 14px; font-weight: 400;">
            No specific reference URLs identified for this investigation.
        </div>
        """

    # Render everything in one cohesive block
    st.html(
        f"""
    <div style="
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 12px;
        padding: 28px;
        margin-top: 32px;
        border: 1px solid #cbd5e1;
    ">
        <div style="
            font-family: 'Poppins', sans-serif;
            font-size: 18px;
            font-weight: 700;
            color: #003366;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: -0.2px;
        ">
            <span style="font-size: 22px;">📚</span>
            <span>Data Sources & References</span>
        </div>
        {source_items_html}
    </div>
    """
    )
