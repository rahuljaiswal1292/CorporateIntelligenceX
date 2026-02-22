import random
import pandas as pd
from datetime import datetime, timedelta


def get_company_data(query: str):
    """
    Simulates an intelligent backend that resolves entity names and returns comprehensive profiling data.
    """
    query = query.upper().strip()

    # --- 1. Entity Resolution (Mock) ---
    if False:  # "EMAAR" in query: (DISABLED for real testing)
        ticker = "EMAAR"
        exchange = "DFM"
        name = "Emaar Properties PJSC"
        sector = "Real Estate"
        profile_type = "RE_DEV"
        desc = """**Emaar Properties** is one of the world's most valuable and admired real estate development companies. With proven competencies in properties, shopping malls & retail, and hospitality & leisure, Emaar shapes new lifestyles with focus on **design excellence**, build quality, and timely delivery.

The company is the developer of the **Burj Khalifa**, the world's tallest building, and **The Dubai Mall**, the world's largest shopping and entertainment destination. Emaar has a significant presence in several key global markets.

**Key business segments include**:
1. **UAE Development**: Master-planned communities including Downtown Dubai, Dubai Marina, and Dubai Hills Estate.
2. **Emaar Malls**: Owner and operator of iconic retail assets.
3. **International**: Property development operations in Egypt, India, Turkey, Pakistan, and Saudi Arabia.
4. **Hospitality**: Owner and operator of Address Hotels + Resorts and Vida Hotels and Resorts."""

        website = "https://www.emaar.com"
        socials = {
            "LinkedIn": "https://linkedin.com/company/emaar",
            "Twitter": "@emaar",
            "Instagram": "@emaardubai",
        }

        shareholders = [
            {"Name": "Public / Free Float", "Type": "Public", "%": "60.0%"},
            {
                "Name": "Investment Corp of Dubai (ICD)",
                "Type": "Government",
                "%": "24.0%",
            },
            {"Name": "Vanguard Group", "Type": "Institutional", "%": "2.0%"},
            {"Name": "BlackRock Inc.", "Type": "Institutional", "%": "1.5%"},
            {"Name": "Other Institutional", "Type": "Institutional", "%": "12.5%"},
        ]
        est_date = "1997"

    elif "NBD" in query or "BANK" in query or "EMIRATES" in query:
        ticker = "ENBD"
        exchange = "DFM"
        name = "Emirates NBD Bank PJSC"
        sector = "Banking"
        profile_type = "BANK"
        desc = """**Emirates NBD** is a leading banking group in the **MENAT** (Middle East, North Africa and Turkey) region. As a **National Banking Champion**, it plays a key role in the UAE's economic growth strategy.

The Group has operations in the UAE, Egypt, India, Turkey, the Kingdom of Saudi Arabia, Singapore, the United Kingdom, Austria, Germany, Russia and Bahrain and representative offices in China and Indonesia.

**Strategic Pillars**:
1. **Retail Banking & Wealth Management**: Examples of digital leadership via **Liv.** and **ENBD X**.
2. **Corporate & Institutional Banking**: Heavyweight in trade finance, project finance, and syndications.
3. **Global Markets & Treasury**: Market maker for AED and regional currencies.
4. **DenizBank**: Significant subsidiary operating in Turkey."""

        website = "https://www.emiratesnbd.com"
        socials = {
            "LinkedIn": "https://linkedin.com/company/emirates-nbd",
            "Twitter": "@EmiratesNBD",
            "Instagram": "@emiratesnbd_ae",
        }

        shareholders = [
            {
                "Name": "Investment Corp of Dubai (ICD)",
                "Type": "Government",
                "%": "55.75%",
            },
            {"Name": "Public / Free Float", "Type": "Public", "%": "44.25%"},
        ]
        est_date = "1963 (Merger 2007)"

    elif "AIR" in query or "ARABIA" in query:
        ticker = "AIRARABIA"
        exchange = "DFM"
        name = "Air Arabia PJSC"
        sector = "Aviation"
        profile_type = "AVIATION"
        desc = """**Air Arabia** is the Middle East and North Africa's first and largest **Low Cost Carrier (LCC)**. We fly you to over 170 destinations spread across the Middle East, North Africa, Asia and Europe.
        
The airline operates hubs in UAE (Sharjah, Abu Dhabi, Ras Al Khaimah), Morocco, Egypt, and Pakistan. It follows a low-cost business model, prioritizing **operational efficiency** and high aircraft utilization.

**Key strengths include**:
- Modern fleet of **Airbus A320** and A321 neo aircraft.
- Strong ancillary revenue generation.
- Joint ventures establishing new national carriers (e.g., Fly Arna, Fly Jinnah)."""

        website = "https://www.airarabia.com"
        socials = {
            "LinkedIn": "https://linkedin.com/company/air-arabia",
            "Twitter": "@airarabia",
            "Instagram": "@airarabiagroup",
        }

        shareholders = [
            {"Name": "Sharjah Asset Management", "Type": "Government", "%": "18.0%"},
            {"Name": "Al Maha Holding", "Type": "Private", "%": "9.0%"},
            {"Name": "Public / Free Float", "Type": "Public", "%": "73.0%"},
        ]
        est_date = "2003"

    elif "ETISALAT" in query or "E&" in query:
        ticker = "EAND"
        exchange = "ADX"
        name = "Etisalat Group (e&)"
        sector = "Telecom"
        profile_type = "TELCO"
        desc = """**e&** (formerly Etisalat Group) is one of the world's leading technology and investment groups. With consolidated net revenue topping AED 53.3 billion, it maintains high credit ratings reflecting its strong balance sheet and proven long-term performance.
        
Headquartered in Abu Dhabi, **e&** was established over four decades ago as the UAE's first telecommunications service provider.

**Business Verticals**:
1. **e& international**: Telecom operations across 16 countries.
2. **e& life**: Consumer digital services (fintech, entertainment).
3. **e& enterprise**: Cloud, cybersecurity, and IoT for governments/corporates.
4. **e& capital**: Investment arm for startup acquisitions."""

        website = "https://www.eand.com"
        socials = {
            "LinkedIn": "https://linkedin.com/company/eand",
            "Twitter": "@eand",
            "Instagram": "@eandgroup",
        }

        shareholders = [
            {
                "Name": "Emirates Investment Authority",
                "Type": "Government",
                "%": "60.0%",
            },
            {"Name": "Public / Free Float", "Type": "Public", "%": "40.0%"},
        ]
        est_date = "1976"

    elif "FAB" in query or "FIRST ABU" in query:
        ticker = "FAB"
        exchange = "ADX"
        name = "First Abu Dhabi Bank PJSC"
        sector = "Banking"
        profile_type = "BANK"
        desc = """**First Abu Dhabi Bank (FAB)** is the UAE's largest bank and one of the world's largest and safest financial institutions. Headquartered in Abu Dhabi, it provides a comprehensive range of financial products and services.
        
FAB offers corporate, investment, and personal banking solutions, with a strong presence in global markets."""

        website = "https://www.bankfab.com"
        socials = {
            "LinkedIn": "https://linkedin.com/company/fab",
            "Twitter": "@FABConnects",
            "Instagram": "@fabconnects",
        }

        shareholders = [
            {"Name": "Mubadala Investment Company", "Type": "Government", "%": "37.9%"},
            {"Name": "Public / Free Float", "Type": "Public", "%": "62.1%"},
        ]
        est_date = "2017 (Merger of NBAD & FGB)"

    else:
        # Generic Fallback
        ticker = "UNKNOWN"
        exchange = "ADX/DFM"
        name = query.title()
        sector = "Diversified"
        profile_type = "GENERIC"
        desc = f"**{name}** is being analyzed by the Corporate Intelligence Agent. Real-time data will be populated shortly from exchange filings and public records."

        website = ""
        socials = {}
        shareholders = []
        est_date = ""

    # --- 2. Generate Dynamic Data ---

    data = {
        "meta": {
            "name": name,
            "ticker": ticker,
            "exchange": exchange,
            "sector": sector,
            "description": desc,
            "website": website,
            "socials": socials,
            "shareholders": shareholders,
            "est_date": est_date,
            "resolved_at": datetime.now().strftime("%H:%M:%S"),
        },
        "financials": {},
        "risk": {},
        "news": [],
        "competitors": [],
        "insights": [],
        "sources": [],
    }

    # Populate specific data points
    if ticker == "EMAAR":
        data["financials"] = {
            "current": {
                "period": "TTM Q3 2024",
                "rev": "AED 26.7B",
                "profit": "AED 11.6B",
                "price": "AED 8.45",
                "trend": "+1.2%",
            },
            "last_year": {
                "period": "FY 2023",
                "rev": "AED 26.0B",
                "profit": "AED 10.8B",
            },
            "last_quarter": {
                "period": "Q3 2024",
                "rev": "AED 6.8B",
                "profit": "AED 2.9B",
                "rev_gro": "+3%",
                "prof_gro": "+8%",
            },
        }
        data["risk"] = {
            "debt_equity": "0.6x",
            "credit_rating": "BBB- (S&P)",
            "interest_cover": "8.4x",
        }
        data["competitors"] = [
            {
                "Company": "Emaar Dev",
                "Mkt Cap": "AED 28B",
                "P/E": "8.5",
                "Rev Growth": "12%",
            },
            {
                "Company": "Aldar",
                "Mkt Cap": "AED 45B",
                "P/E": "14.2",
                "Rev Growth": "8%",
            },
            {
                "Company": "Damac",
                "Mkt Cap": "Private",
                "P/E": "N/A",
                "Rev Growth": "5%",
            },
            {
                "Company": "Deyaar",
                "Mkt Cap": "AED 3.8B",
                "P/E": "9.1",
                "Rev Growth": "6.5%",
            },
            {
                "Company": "Union Prop",
                "Mkt Cap": "AED 1.5B",
                "P/E": "N/A",
                "Rev Growth": "-2%",
            },
        ]
        data["sources"] = [
            {
                "title": "Emaar Q3 2024 Earnings Release",
                "url": "https://www.emaar.com/investor-relations/financials",
            },
            {
                "title": "Emaar FY 2023 Integrated Report",
                "url": "https://www.emaar.com/annual-reports/2023",
            },
            {
                "title": "DFM Market Disclosure - The Heights Launch",
                "url": "https://www.dfm.ae/issuers/emaar",
            },
        ]
        data["insights"] = [
            {
                "category": "Lending & Refinancing Accuracy",
                "finding": "AED 2.5B Sukuk Maturing Dec 2025",
                "source": "'Borrowings' Note in Q3 Financials",
                "trigger": "Refinancing Opportunity",
                "action": "Pitch Refinancing: Competitor bank facility maturing in 12 months; potential for 50bps pricing play.",
            },
            {
                "category": "Trade Finance & FX Wallet",
                "finding": "28% Revenue from International Operations (Egypt, India)",
                "source": "'Segment Reporting' Note",
                "trigger": "Cross-Sell FX Hedging",
                "action": "High FX volatility risk detected (EGP/INR); offer forward contracts and treasury solutions.",
            },
            {
                "category": "Operational Efficiency",
                "finding": "Receivables +15% vs Revenue +5%",
                "source": "Balance Sheet & Cash Flow Stmt",
                "trigger": "Working Capital Gap",
                "action": "Client's cash cycle is stretching; pitch a Supply Chain Finance (SCF) program to improve liquidity.",
            },
            {
                "category": "KYC & Lifecycle Automation",
                "finding": "Trade License Expiring in 4 Months",
                "source": "DED Registry Scan",
                "trigger": "Administrative Stickiness",
                "action": "Trade License expires May 2026. Action: Pre-populate renewal form and send as 'Value-Added' service.",
            },
            {
                "category": "NTB vs. ETB Strategy",
                "finding": "New 'The Heights' Masterplan Announced",
                "source": "'Subsequent Events' / Press Release",
                "trigger": "Project Finance (NTB)",
                "action": "New CapEx requirement identified. Pitch Project Finance lead for this specific development.",
            },
        ]

    elif ticker == "ENBD":
        data["financials"] = {
            "current": {
                "period": "FY 2024",
                "rev": "AED 43.0B",
                "profit": "AED 21.5B",
                "price": "AED 17.50",
                "trend": "+0.5%",
            },
            "last_year": {
                "period": "FY 2023",
                "rev": "AED 39.5B",
                "profit": "AED 18.0B",
            },
            "last_quarter": {
                "period": "Q4 2024",
                "rev": "AED 11.2B",
                "profit": "AED 5.3B",
                "rev_gro": "+8%",
                "prof_gro": "+12%",
            },
        }
        data["risk"] = {
            "debt_equity": "N/A (Bank)",
            "credit_rating": "A+ (Fitch)",
            "interest_cover": "N/A",
        }
        data["competitors"] = [
            {
                "Company": "FAB",
                "Mkt Cap": "AED 180B",
                "P/E": "12.5",
                "Rev Growth": "4%",
            },
            {
                "Company": "ADCB",
                "Mkt Cap": "AED 65B",
                "P/E": "10.2",
                "Rev Growth": "6%",
            },
            {"Company": "DIB", "Mkt Cap": "AED 42B", "P/E": "8.9", "Rev Growth": "7%"},
            {
                "Company": "Mashreq",
                "Mkt Cap": "AED 38B",
                "P/E": "9.5",
                "Rev Growth": "15%",
            },
            {
                "Company": "RAKBANK",
                "Mkt Cap": "AED 9B",
                "P/E": "8.1",
                "Rev Growth": "5%",
            },
        ]
        data["sources"] = [
            {
                "title": "Emirates NBD FY 2024 Results Presentation",
                "url": "https://www.emiratesnbd.com/en/investor-relations",
            },
            {
                "title": "Basel III Pillar 3 Disclosure",
                "url": "https://www.centralbank.ae/en/regulations",
            },
        ]
        data["insights"] = [
            {
                "category": "Lending & Refinancing Accuracy",
                "finding": "Robust Interbank Liquidity (LCR 165%)",
                "source": "Liquidity Coverage Ratio (LCR) Disclosure",
                "trigger": "Treasury Placement",
                "action": "Excess liquidity detected. Pitch Reverse Repo or short-term placement opportunities to optimize yield.",
            },
            {
                "category": "Trade Finance & FX Wallet",
                "finding": "Expansion in KSA (18% Asset Growth)",
                "source": "Management Discussion & Analysis",
                "trigger": "Cross-Border Corridors",
                "action": "Growing SAR exposure. Offer specialized KSA-UAE trade corridors and settlement layers.",
            },
            {
                "category": "Operational Efficiency",
                "finding": "Cost-to-Income Ratio improved to 28%",
                "source": "Income Statement",
                "trigger": "Digital Synergy",
                "action": "Efficiency driven by digital adoption. Pitch API-banking integration for their corporate clients.",
            },
            {
                "category": "KYC & Lifecycle Automation",
                "finding": "License Valid until 2099 (Perpetual/Charter)",
                "source": "Central Bank Registry",
                "trigger": "Compliance Update",
                "action": "Confirm UBO details for recent board changes (if any) to ensure clean KYC file.",
            },
            {
                "category": "NTB vs. ETB Strategy",
                "finding": "Acquisition of new Wealth Tech platform",
                "source": "Subsequent Events",
                "trigger": "M&A Advisory (ETB)",
                "action": "Client is active in M&A. Position our Investment Banking team for future advisory mandates.",
            },
        ]

    elif ticker == "FAB":
        data["financials"] = {
            "current": {
                "period": "FY 2024",
                "rev": "AED 28.5B",
                "profit": "AED 16.4B",
                "price": "AED 13.60",
                "trend": "+1.1%",
            },
            "last_year": {
                "period": "FY 2023",
                "rev": "AED 27.0B",
                "profit": "AED 15.0B",
            },
            "last_quarter": {
                "period": "Q4 2024",
                "rev": "AED 7.2B",
                "profit": "AED 4.1B",
                "rev_gro": "+5%",
                "prof_gro": "+8%",
            },
        }
        data["risk"] = {
            "debt_equity": "N/A",
            "credit_rating": "AA- (Fitch)",
            "interest_cover": "N/A",
        }
        data["competitors"] = [
            {
                "Company": "Emirates NBD",
                "Mkt Cap": "AED 110B",
                "P/E": "5.5",
                "Rev Growth": "15%",
            },
            {
                "Company": "ADCB",
                "Mkt Cap": "AED 64B",
                "P/E": "8.5",
                "Rev Growth": "10%",
            },
            {"Company": "DIB", "Mkt Cap": "AED 41B", "P/E": "7.2", "Rev Growth": "9%"},
        ]
        data["sources"] = [
            {
                "title": "FAB Earnings Release",
                "url": "https://www.bankfab.com/en-ae/about-fab/investor-relations",
            }
        ]
        data["insights"] = [
            {
                "category": "Global Markets",
                "finding": "Strong International Expansion",
                "source": "Investor Presentation",
                "trigger": "Cross-Border Flows",
                "action": "Leverage global network for trade finance deals.",
            }
        ]

    elif ticker == "EAND":
        data["financials"] = {
            "current": {
                "period": "TTM Q3 2024",
                "rev": "AED 52.4B",
                "profit": "AED 10.1B",
                "price": "AED 18.42",
                "trend": "-0.5%",
            },
            "last_year": {
                "period": "FY 2023",
                "rev": "AED 51.0B",
                "profit": "AED 9.8B",
            },
            "last_quarter": {
                "period": "Q3 2024",
                "rev": "AED 13.1B",
                "profit": "AED 2.5B",
                "rev_gro": "+2%",
                "prof_gro": "+4%",
            },
        }
        data["risk"] = {
            "debt_equity": "1.1x",
            "credit_rating": "AA- (S&P)",
            "interest_cover": "12.5x",
        }
        data["competitors"] = [
            {
                "Company": "Du (EITC)",
                "Mkt Cap": "AED 24B",
                "P/E": "14.5",
                "Rev Growth": "5.1%",
            },
            {
                "Company": "Ooredoo",
                "Mkt Cap": "QAR 28B",
                "P/E": "12.1",
                "Rev Growth": "2.8%",
            },
            {
                "Company": "Vodafone",
                "Mkt Cap": "GBP 19B",
                "P/E": "11.2",
                "Rev Growth": "1.4%",
            },
            {
                "Company": "STC",
                "Mkt Cap": "SAR 200B",
                "P/E": "16.5",
                "Rev Growth": "6%",
            },
            {
                "Company": "Zain Group",
                "Mkt Cap": "KWD 2.5B",
                "P/E": "10.8",
                "Rev Growth": "2%",
            },
        ]
        data["sources"] = [
            {
                "title": "e& Q3 2024 Financial Report",
                "url": "https://www.eand.com/investors",
            },
            {"title": "ADX Disclosure - Vodafone Stake", "url": "https://www.adx.ae"},
        ]
        data["insights"] = [
            {
                "category": "Lending & Refinancing Accuracy",
                "finding": "EUR 2B Bond Maturing Q4 2025",
                "source": "'Borrowings' Note",
                "trigger": "Refinancing Opportunity",
                "action": "Bond maturity approaching. Pitch bridge financing or lead arranger role for new issuance.",
            },
            {
                "category": "Trade Finance & FX Wallet",
                "finding": "High Capex on 5G Infrastructure Imports",
                "source": "Cash Flow from Investing",
                "trigger": "Import LCs",
                "action": "Significant equipment imports detected. Pitch Import Letters of Credit and Guarantees.",
            },
            {
                "category": "Operational Efficiency",
                "finding": "Payables Days increased to 95 days",
                "source": "Working Capital Analysis",
                "trigger": "Supplier Payment",
                "action": "Stretching payables. Offer Vendor Financing/Factoring to their key suppliers.",
            },
            {
                "category": "KYC & Lifecycle Automation",
                "finding": "License Expires Dec 2026",
                "source": "DED Search",
                "trigger": "Cycle Management",
                "action": "Set reminder for Q3 2026 to initiate proactive renewal capability.",
            },
            {
                "category": "NTB vs. ETB Strategy",
                "finding": "Stake increase in Vodafone Group",
                "source": "Investment Disclosure",
                "trigger": "Strategic Acquisition Finance",
                "action": "Strategic stake building. Offer acquisition financing or currency hedging for GBP exposure.",
            },
        ]

    else:  # Genuine Fallback (Empty/Loading State)
        data["financials"] = {
            "current": {
                "period": "TBD",
                "rev": "---",
                "profit": "---",
                "price": "---",
                "trend": "---",
            },
            "last_year": {"period": "---", "rev": "---", "profit": "---"},
            "last_quarter": {
                "period": "---",
                "rev": "---",
                "profit": "---",
                "rev_gro": "---",
                "prof_gro": "---",
            },
        }
        data["risk"] = {
            "debt_equity": "---",
            "credit_rating": "---",
            "interest_cover": "---",
        }
        data["competitors"] = []
        data["sources"] = []
        data["insights"] = []

    # Simulate Chart Data
    dates = pd.date_range(start="2024-01-01", periods=100)

    price_str = data["financials"]["current"].get("price", "---")
    try:
        if " " in price_str and price_str != "---":
            base_price = float(price_str.split(" ")[1].replace(",", ""))
        else:
            base_price = 10.0  # Default/Fallback
    except:
        base_price = 10.0

    volatility = base_price * 0.02

    open_data = [
        base_price + random.uniform(-volatility, volatility) for _ in range(100)
    ]
    close_data = [
        o + random.uniform(-volatility / 2, volatility / 2) for o in open_data
    ]
    high_data = [
        max(o, c) + random.uniform(0, volatility / 3)
        for o, c in zip(open_data, close_data)
    ]
    low_data = [
        min(o, c) - random.uniform(0, volatility / 3)
        for o, c in zip(open_data, close_data)
    ]

    data["chart"] = {
        "dates": dates,
        "open": open_data,
        "high": high_data,
        "low": low_data,
        "close": close_data,
    }

    return data
