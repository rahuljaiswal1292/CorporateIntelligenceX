import streamlit as st


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
                "license_number": "DED-123456",
                "activity_type": "Banking & Financial Services",
                "status": "Active",
                "expiry_date": "31-Dec-2027",
                "trade_name": "Emirates NBD Bank PJSC",
                "url": "https://www.ded.ae",
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
            "Analyst Agent completed successfully",
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
            Corporate Intelligence Dashboard
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

    # === SECTION 2 & 3: COMPANY PROFILE + FINANCIALS - Two Column Layout ===
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
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
            <span style="font-size: 24px;">🏢</span>
            <span>Company Profile</span>
        </div>
        """
        )

        if meta:
            company_name = meta.get("name", "Unknown Company")
            description = meta.get("description", "No description available")
            website = meta.get("website", "#")

            # Get DED data - handle both single license (dict) and multiple licenses (list)
            ded_data = enrichments.get("ded", {})

            # Normalize to list format
            if isinstance(ded_data, dict) and ded_data:
                licenses = [ded_data]  # Single license
            elif isinstance(ded_data, list):
                licenses = ded_data  # Multiple licenses
            else:
                licenses = []  # No licenses

            st.html(
                f"""
            <div style="
                background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 28px;
                box-shadow: 0 4px 16px rgba(0, 51, 102, 0.08);
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
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Industry</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('sector', 'N/A')}</div>
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Founded</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('founded', 'N/A')}</div>
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Headquarters</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('headquarters', 'N/A')}</div>
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">Exchange</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 15px; font-weight: 600;">{meta.get('exchange', 'N/A')}: {meta.get('ticker', '')}</div>
                    </div>
                </div>
            </div>
            """
            )

            # DED License Information - Separate section below profile
            if licenses:
                license_count = len(licenses)
                st.html(
                    f"""
                <div style="
                    font-family: 'Poppins', sans-serif;
                    color: #003366;
                    font-size: 15px;
                    font-weight: 700;
                    margin-top: 20px;
                    margin-bottom: 12px;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                ">
                    <span style="font-size: 18px;">🏛️</span>
                    <span>DED License Information {f'({license_count} Licenses)' if license_count > 1 else ''}</span>
                </div>
                """
                )

                # Display licenses in a grid (2 columns for multiple licenses, 1 for single)
                if license_count == 1:
                    cols = st.columns(1)
                else:
                    cols = st.columns(2)

                for idx, lic in enumerate(licenses):
                    license_number = lic.get("license_number", "N/A")
                    activity_type = lic.get("activity_type", "N/A")
                    lic_status = lic.get("status", "N/A")
                    expiry_date = lic.get("expiry_date", "N/A")
                    trade_name = lic.get("trade_name", "")

                    with cols[idx % len(cols)]:
                        st.html(
                            f"""
                        <div style="
                            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
                            border: 1px solid #e2e8f0;
                            border-left: 3px solid #0077ff;
                            border-radius: 8px;
                            padding: 16px;
                            margin-bottom: 12px;
                            box-shadow: 0 2px 8px rgba(0, 51, 102, 0.06);
                        ">
                            {f'<div style="font-family: Poppins, sans-serif; color: #003366; font-size: 13px; font-weight: 700; margin-bottom: 12px;">{trade_name}</div>' if trade_name else ''}
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                                <div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">License No.</div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 13px; font-weight: 600;">{license_number}</div>
                                </div>
                                <div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Status</div>
                                    <div style="font-family: 'Poppins', sans-serif; color: {'#10b981' if lic_status.lower() == 'active' else '#ef4444' if lic_status.lower() == 'expired' else '#1e293b'}; font-size: 13px; font-weight: 700;">{lic_status}</div>
                                </div>
                                <div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Activity Type</div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 12px; font-weight: 600;">{activity_type}</div>
                                </div>
                                <div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Expiry Date</div>
                                    <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 13px; font-weight: 600;">{expiry_date}</div>
                                </div>
                            </div>
                        </div>
                        """
                        )
        else:
            st.info("Company profile data pending...")

    with col_right:
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
            <span style="font-size: 24px;">💰</span>
            <span>Financial Snapshot</span>
        </div>
        """
        )

        if financials and "current" in financials:
            curr = financials.get("current", {})

            # Primary Metrics - Revenue & Profit
            st.html(
                f"""
            <div style="
                background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 16px;
                box-shadow: 0 4px 16px rgba(30, 58, 138, 0.3);
                color: white;
            ">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Total Revenue</div>
                        <div style="font-family: 'Poppins', sans-serif; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("rev", "N/A")}</div>
                        {f'<div style="font-family: Poppins, sans-serif; color: #4ade80; font-size: 12px; font-weight: 600; margin-top: 4px;">↑ {curr.get("trend", "")}</div>' if curr.get("trend") else ''}
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.8); font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.8px;">Net Profit</div>
                        <div style="font-family: 'Poppins', sans-serif; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">{curr.get("profit", "N/A")}</div>
                    </div>
                </div>
            </div>
            """
            )

            # Key Banking Ratios - 3 cards with professional blue palette
            roe = curr.get("roe", "N/A")
            roa = curr.get("roa", "N/A")
            npl_ratio = curr.get("npl_ratio", "N/A")

            st.html(
                f"""
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
                <div style="
                    background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
                    border-radius: 10px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(8, 145, 178, 0.25);
                    text-align: center;
                ">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.9); font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">ROE</div>
                    <div style="font-family: 'Poppins', sans-serif; color: white; font-size: 22px; font-weight: 800;">{roe}</div>
                </div>
                <div style="
                    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                    border-radius: 10px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(30, 64, 175, 0.25);
                    text-align: center;
                ">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.9); font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">ROA</div>
                    <div style="font-family: 'Poppins', sans-serif; color: white; font-size: 22px; font-weight: 800;">{roa}</div>
                </div>
                <div style="
                    background: linear-gradient(135deg, #475569 0%, #64748b 100%);
                    border-radius: 10px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(71, 85, 105, 0.25);
                    text-align: center;
                ">
                    <div style="font-family: 'Poppins', sans-serif; color: rgba(255, 255, 255, 0.9); font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">NPL Ratio</div>
                    <div style="font-family: 'Poppins', sans-serif; color: white; font-size: 22px; font-weight: 800;">{npl_ratio}</div>
                </div>
            </div>
            """
            )

            # Additional Metrics - 2x2 Grid
            capital_adequacy = curr.get("capital_adequacy", "N/A")
            cost_to_income = curr.get("cost_to_income", "N/A")
            lcr = curr.get("liquidity_coverage_ratio", "N/A")
            price = curr.get("price", "N/A")

            st.html(
                f"""
            <div style="
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0, 51, 102, 0.06);
            ">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Capital Adequacy</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 18px; font-weight: 700;">{capital_adequacy}</div>
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Cost-to-Income</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 18px; font-weight: 700;">{cost_to_income}</div>
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">LCR</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #1e293b; font-size: 18px; font-weight: 700;">{lcr}</div>
                    </div>
                    <div>
                        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 9px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.5px;">Stock Price</div>
                        <div style="font-family: 'Poppins', sans-serif; color: #0077ff; font-size: 18px; font-weight: 700;">{price}</div>
                    </div>
                </div>
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
    news_data = enrichments.get("news", {})
    news_articles = news_data.get("sources", []) if isinstance(news_data, dict) else []

    if not news_articles:
        news_articles = data.get("news_articles", [])

    if news_articles and len(news_articles) > 0:
        # Display top 3 news in a grid
        news_cols = st.columns(3)
        for idx, article in enumerate(news_articles[:3]):
            if isinstance(article, dict):
                title = article.get("title", "Untitled")
                url = article.get("url", "#")
                source = article.get("source", "News Source")
                date = article.get("date", "")

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
        <span>Stock Performance & Market Trends</span>
    </div>
    """
    )

    # Placeholder for stock chart
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
        ">Stock performance chart will be displayed here</div>
        <div style="
            font-family: 'Poppins', sans-serif;
            color: #94a3b8;
            font-size: 13px;
            margin-top: 8px;
        ">Historical price data, volume, and technical indicators</div>
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
                text = insight.get("text", insight.get("insight", ""))

                with insight_cols[idx % 2]:
                    st.html(
                        f"""
                    <div style="
                        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                        border-left: 4px solid #0077ff;
                        border-radius: 12px;
                        padding: 20px;
                        margin-bottom: 16px;
                        box-shadow: 0 2px 8px rgba(0, 51, 102, 0.06);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateX(4px)'; this.style.boxShadow='0 4px 16px rgba(0, 119, 255, 0.12)';" 
                       onmouseout="this.style.transform='translateX(0)'; this.style.boxShadow='0 2px 8px rgba(0, 51, 102, 0.06)';">
                        <div style="
                            font-family: 'Poppins', sans-serif;
                            color: #0077ff;
                            font-weight: 700;
                            font-size: 11px;
                            text-transform: uppercase;
                            margin-bottom: 10px;
                            letter-spacing: 0.8px;
                        ">{category}</div>
                        <div style="
                            font-family: 'Poppins', sans-serif;
                            color: #334155;
                            line-height: 1.6;
                            font-size: 14px;
                            font-weight: 400;
                        ">{text}</div>
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

    # === SECTION 8: DATA SOURCES - Elegant Footer ===
    st.html(
        """
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
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: -0.2px;
        ">
            <span style="font-size: 22px;">📚</span>
            <span>Data Sources & References</span>
        </div>
    """
    )

    sources_count = 0
    if enrichments:
        if enrichments.get("wikipedia"):
            sources_count += 1
        if enrichments.get("news"):
            sources_count += 1
        if enrichments.get("serp"):
            sources_count += 1

    wiki_status = "✓" if enrichments.get("wikipedia") else "○"
    wiki_color = "#10b981" if enrichments.get("wikipedia") else "#cbd5e1"
    news_status = "✓" if enrichments.get("news") else "○"
    news_color = "#10b981" if enrichments.get("news") else "#cbd5e1"
    serp_status = "✓" if enrichments.get("serp") else "○"
    serp_color = "#10b981" if enrichments.get("serp") else "#cbd5e1"

    st.html(
        f"""
        <div style="font-family: 'Poppins', sans-serif; color: #64748b; font-size: 14px; margin-bottom: 16px; font-weight: 400;">
            Analysis based on <strong style="color: #003366; font-weight: 700;">{sources_count} verified data sources</strong>
        </div>
        <div style="display: flex; gap: 24px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="color: {wiki_color}; font-size: 18px; font-weight: 700;">{wiki_status}</span>
                <span style="font-family: 'Poppins', sans-serif; color: #475569; font-size: 14px; font-weight: 600;">Wikipedia</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="color: {news_color}; font-size: 18px; font-weight: 700;">{news_status}</span>
                <span style="font-family: 'Poppins', sans-serif; color: #475569; font-size: 14px; font-weight: 600;">News Articles</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="color: {serp_color}; font-size: 18px; font-weight: 700;">{serp_status}</span>
                <span style="font-family: 'Poppins', sans-serif; color: #475569; font-size: 14px; font-weight: 600;">Web Search</span>
            </div>
        </div>
    </div>
    """
    )
