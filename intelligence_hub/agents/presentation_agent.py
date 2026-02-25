import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from intelligence_hub.agents.base_agent import BaseAgent
from intelligence_hub.graph.state import AgentState
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore


class PresentationAgent(BaseAgent):
    """
    Final Agent to consolidate and format all data for the Frontend UI.
    """

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="Presentation Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        return True, "Always run to format output for UI"

    def execute(self, state: AgentState) -> Dict:
        """Required by BaseAgent. Calls run()."""
        return self.run(state)

    def _format_currency(self, value: Any, unit: Optional[str] = None) -> str:
        """Format numbers/strings into human-readable currency (e.g. AED 6.7B)."""
        if value is None or value == "":
            return "N/A"

        # If already formatted string with AED/B/M, just return it
        if isinstance(value, str) and ("AED" in value or "B" in value or "M" in value):
            return value

        try:
            val_float = float(str(value).replace(",", ""))
            # Handle unit scaling if provided (e.g. from PDF 'thousands')
            unit_lower = unit.lower() if unit else ""
            if "thousand" in unit_lower or "000" in unit_lower:
                val_float *= 1000
            elif "million" in unit_lower:
                val_float *= 1_000_000

            if val_float >= 1_000_000_000:
                return f"AED {val_float / 1_000_000_000:.1f}B"
            elif val_float >= 1_000_000:
                return f"AED {val_float / 1_000_000:.1f}M"
            else:
                return f"AED {val_float:,.0f}"
        except:
            return str(value)

    def run(self, state: AgentState):
        """
        Consolidates state into the final UI-ready structure matching final_demo.json.
        """
        self.company_name = state.get("company_name", "Unknown")
        ticker = state.get("ticker", "Unknown")
        exchange = state.get("exchange", "Unknown")
        self.log(
            f"Formatting final dashboard data for {self.company_name} ({ticker})..."
        )

        enrichments = state.get("enrichments", {}) or {}
        if isinstance(enrichments, list):
            enrichments = (
                enrichments[0]
                if enrichments and isinstance(enrichments[0], dict)
                else {}
            )

        financial_data = state.get("financial_data", {}) or {}
        if isinstance(financial_data, list):
            financial_data = (
                financial_data[0]
                if financial_data and isinstance(financial_data[0], dict)
                else {}
            )

        final_report = state.get("final_report", {}) or {}

        # Defensive check for final_report (handled list case from legacy/LLM errors)
        if isinstance(final_report, list):
            self.log(
                "Presentation Agent: final_report is a list, attempting to resolve to dict",
                "WARNING",
            )
            if len(final_report) > 0 and isinstance(final_report[0], dict):
                final_report = final_report[0]
            else:
                final_report = {}

        pdf_results = state.get("pdf_results", []) or []

        # 1. Meta Mapping
        # 1. Resolve Description (Prevent mock leakage)
        raw_desc = (
            final_report.get("Executive_summary")
            or enrichments.get("description")
            or financial_data.get("profile", {}).get("description", "")
        )

        # Check if the description is the generic mock placeholder from mock_data.py
        mock_marker = "is being analyzed by the Corporate Intelligence Agent"
        if raw_desc and mock_marker in raw_desc:
            # Try to build a better one or clear it
            if enrichments.get("name"):
                raw_desc = f"{enrichments['name']} analysis in progress..."
            else:
                raw_desc = ""

        meta = {
            "name": self.company_name,
            "description": raw_desc or "No description available.",
            "website": enrichments.get("official_website")
            or enrichments.get("website")
            or state.get("website")
            or financial_data.get("profile", {}).get("website"),
            "founded": enrichments.get("knowledge_graph", {}).get("founded")
            or financial_data.get("profile", {}).get("est_date"),
            "headquarters": enrichments.get("knowledge_graph", {}).get("headquarters")
            or financial_data.get("profile", {}).get("headquarters"),
            "sector": enrichments.get("knowledge_graph", {}).get("type")
            or financial_data.get("profile", {}).get("sector")
            or financial_data.get("profile", {}).get("industry"),
            "industry": enrichments.get("knowledge_graph", {}).get("type")
            or financial_data.get("profile", {}).get("industry")
            or financial_data.get("profile", {}).get("sector"),
            "exchange": exchange,
            "ticker": ticker,
        }

        # 2. Financials Mapping
        # Extract from newest PDF if available
        current_metrics = {}
        last_year_metrics = {}

        if pdf_results:
            # pdf_results is now optimized by PdfAgent to contain the best candidate(s)
            # We still prefer an explicit 'annual' flag if multiple were somehow provided
            annual_reports = [
                pdf
                for pdf in pdf_results
                if "annual" in str(pdf.get("meta", {}).get("period", "")).lower()
            ]

            target_pdf = annual_reports[0] if annual_reports else pdf_results[0]

            fin_full = target_pdf.get("financials", {})
            # Handle user requested nested format or legacy flat format
            fin = fin_full.get("current_period") or fin_full
            meta_pdf = target_pdf.get("meta", {})

            # Helper to get float value
            def to_f(obj):
                if not obj or not isinstance(obj, dict):
                    return None
                val = obj.get("current")
                if val is None:
                    return None
                try:
                    return float(str(val).replace(",", ""))
                except:
                    return None

            rev_block = fin.get("revenue") or {}
            unit = rev_block.get("unit")
            current_metrics = {
                "period": meta_pdf.get("period")
                or meta_pdf.get("report_date")
                or "Latest Report",
                "rev": self._format_currency(rev_block.get("current"), unit),
                "profit": self._format_currency(
                    (fin.get("net_income") or {}).get("current"), unit
                ),
                "assets": self._format_currency(
                    (fin.get("total_assets") or {}).get("current"), unit
                ),
                "liabilities": self._format_currency(
                    (fin.get("total_liabilities") or {}).get("current"), unit
                ),
                "equity": self._format_currency(
                    (fin.get("equity") or {}).get("current"), unit
                ),
            }

            # --- Deterministic Ratio Calculations ---
            rev = to_f(fin.get("revenue"))
            net_income = to_f(fin.get("net_income"))
            equity = to_f(fin.get("equity"))
            assets = to_f(fin.get("total_assets"))
            opex = to_f(fin.get("operating_expenses"))
            int_inc = to_f(fin.get("interest_income"))
            int_exp = to_f(fin.get("interest_expense"))
            npl = to_f(fin.get("impaired_loans"))

            if net_income is not None and equity and equity != 0:
                current_metrics["roe"] = f"{(net_income / equity) * 100:.2f}%"

            if net_income is not None and rev and rev != 0:
                current_metrics["npm"] = f"{(net_income / rev) * 100:.2f}%"

            if opex is not None and rev and rev != 0:
                current_metrics["cost_to_income"] = f"{(opex / rev) * 100:.2f}%"

            if int_inc is not None and int_exp is not None and assets and assets != 0:
                # Simplified NIM calculation
                current_metrics["nim"] = f"{((int_inc - int_exp) / assets) * 100:.2f}%"

            if npl is not None and assets and assets != 0:
                current_metrics["npl_ratio"] = f"{(npl / assets) * 100:.2f}%"

            # Fallback for predefined ratios if they exist in raw PDF output
            for ratio_key in ["roa", "capital_adequacy", "liquidity_coverage_ratio"]:
                if ratio_key in fin and ratio_key not in current_metrics:
                    current_metrics[ratio_key] = fin[ratio_key]

            ni_block = fin.get("net_income") or {}
            last_year_metrics = {
                "period": "Previous Year",
                "rev": self._format_currency(rev_block.get("previous"), unit),
                "profit": self._format_currency(ni_block.get("previous"), unit),
            }

        # Fallback to daily_summary or scraped data
        daily_block = financial_data.get("daily_summary") or {}
        daily = daily_block.get("data", [])

        chart_data = {}
        if daily:
            try:
                # Determine exchange to handle date format and column names
                is_adx = exchange.lower() == "adx"
                date_fmt = "%Y-%m-%d" if is_adx else "%d-%m-%Y"

                # Sort by date ascending for the chart
                sorted_daily = sorted(
                    daily, key=lambda x: datetime.strptime(x["Date"], date_fmt)
                )

                # ADX uses 'Close' and 'Change %', DFM uses 'Last' and 'Change Percentage'
                close_key = "Close" if is_adx else "Last"

                chart_data = {
                    "dates": [
                        datetime.strptime(d["Date"], date_fmt).strftime("%Y-%m-%d")
                        for d in sorted_daily
                    ],
                    "open": [d["Open"] for d in sorted_daily],
                    "high": [d["High"] for d in sorted_daily],
                    "low": [d["Low"] for d in sorted_daily],
                    "close": [d.get(close_key, d.get("Last")) for d in sorted_daily],
                    "volume": [d["Volume"] for d in sorted_daily],
                }
            except Exception as e:
                self.log(f"Failed to format chart data: {e}", "WARNING")

        if daily and not current_metrics.get("price"):
            # Sort by date descending to get the most recent day for metrics
            is_adx = exchange.lower() == "adx"
            date_fmt = "%Y-%m-%d" if is_adx else "%d-%m-%Y"

            try:
                sorted_for_metrics = sorted(
                    daily,
                    key=lambda x: datetime.strptime(x["Date"], date_fmt),
                    reverse=True,
                )
                latest_day = sorted_for_metrics[0]

                close_key = "Close" if is_adx else "Last"
                trend_key = "Change %" if is_adx else "Change Percentage"

                current_metrics["price"] = (
                    f"AED {latest_day.get(close_key, latest_day.get('Last', 'N/A'))}"
                )
                current_metrics["trend"] = latest_day.get(trend_key, "")
            except Exception as e:
                self.log(f"Failed to extract latest metrics: {e}", "WARNING")

        competitor_analysis = enrichments.get("Competitor Analysis") or {}
        if isinstance(competitor_analysis, list):
            competitor_analysis = (
                competitor_analysis[0]
                if competitor_analysis and isinstance(competitor_analysis[0], dict)
                else {}
            )
        comp_data_block = competitor_analysis.get("data") or {}
        if isinstance(comp_data_block, list):
            comp_data_block = (
                comp_data_block[0]
                if comp_data_block and isinstance(comp_data_block[0], dict)
                else {}
            )

        financials = {
            "current": current_metrics,
            "last_year": last_year_metrics,
            "market_cap": comp_data_block.get("market_cap") or "N/A",
        }

        # --- FY 2025 JSON Lookup Support ---
        # If the ticker exists in our curated fy2025_financials.json, use it to override/enrich
        try:
            # Assume file is in the project root (CWD is usually root)
            json_path = os.path.join(os.getcwd(), "fy2025_financials.json")
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    fy_data = json.load(f)

                # Check for ticker match (case-insensitive for robustness)
                ticker_upper = ticker.upper()
                if ticker_upper in fy_data:
                    self.log(
                        f"Found curated FY 2025 data for {ticker_upper}, injecting..."
                    )
                    curated = fy_data[ticker_upper]

                    # Merge current metrics
                    financials["current"] = curated["current"].copy()

                    # Merge last year
                    financials["last_year"] = curated["last_year"]

                    # Merge market cap
                    if curated.get("market_cap") and curated["market_cap"] != "N/A":
                        financials["market_cap"] = curated["market_cap"]
        except Exception as e:
            self.log(f"Failed to lookup FY 2025 curated data: {e}", "WARNING")

        # 3. Enrichments Mapping
        # News: Rename link -> url, published -> date, and generate summary
        news_articles = []
        news_block = enrichments.get("news") or {}

        # Robust extraction for results from various news agents
        raw_articles = []
        if isinstance(news_block, dict):
            raw_articles = news_block.get("articles", []) or news_block.get(
                "sources", []
            )
        elif isinstance(news_block, list):
            raw_articles = news_block

        for art in raw_articles:
            if not isinstance(art, dict):
                continue
            news_articles.append(
                {
                    "title": art.get("title") or art.get("headline"),
                    "url": art.get("url") or art.get("link"),
                    "source": art.get("source") or art.get("publisher"),
                    "date": art.get("date")
                    or art.get("published")
                    or art.get("published_date"),
                }
            )

        news_summary = ""
        if news_articles:
            news_summary = self._generate_news_summary(news_articles)

        # 4. Shareholder Mapping
        sh_raw = enrichments.get("shareholders") or {}
        shareholder_data = (
            sh_raw.get("data")
            if isinstance(sh_raw, dict) and "data" in sh_raw
            else sh_raw
        )

        # Wikipedia URL Extraction from sources
        wiki_url = None
        sources = financial_data.get("sources", []) or []
        for src in sources:
            if not src:
                continue
            if (
                "wikipedia" in str(src.get("title", "")).lower()
                or "wikipedia" in str(src.get("url", "")).lower()
            ):
                wiki_url = src.get("url")
                break
        if not wiki_url:
            wiki_block = enrichments.get("wikipedia") or {}
            wiki_url = wiki_block.get("url") or wiki_block.get("wikipedia_url")

        # SERP Count
        meta_block = enrichments.get("_metadata") or {}
        serp_count = meta_block.get("serp_api_calls", 0)

        # DED Mapping
        ded_raw = enrichments.get("uae_ded_license") or {}
        ded_info = (
            ded_raw.get("data")
            if isinstance(ded_raw, dict) and "data" in ded_raw
            else ded_raw
        )

        enrichments_block = {
            "news": {"sources": news_articles, "summary": news_summary},
            "wikipedia": {"url": wiki_url},
            "serp": {"count": serp_count},
            "ded": ded_info,
            "shareholders": shareholder_data,
        }

        # --- Aggregate Sources for "Data Sources and References" ---
        data_sources = []

        # 1. Official Website
        if meta.get("website") and meta["website"] != "#":
            data_sources.append(
                {
                    "title": "Official Website",
                    "url": meta["website"],
                    "type": "official",
                }
            )

        # 2. Wikipedia
        if wiki_url:
            data_sources.append(
                {"title": "Wikipedia Profile", "url": wiki_url, "type": "reference"}
            )

        # 3. News Articles (Top 5)
        for art in news_articles[:5]:
            if art.get("url"):
                data_sources.append(
                    {
                        "title": art.get("title", "News Article"),
                        "url": art.get("url"),
                        "type": "news",
                        "source": art.get("source"),
                    }
                )

        # 4. PDF Reports
        doc_urls = state.get("doc_urls", []) or []
        for url in doc_urls:
            if isinstance(url, str) and url.lower().endswith(".pdf"):
                data_sources.append(
                    {"title": "Corporate Disclosure (PDF)", "url": url, "type": "pdf"}
                )
            elif isinstance(url, dict) and url.get("url"):
                data_sources.append(
                    {
                        "title": url.get("title", "Disclosure"),
                        "url": url["url"],
                        "type": "disclosure",
                    }
                )

        # 5. Scraper Sources
        scraper_sources = financial_data.get("sources", []) or []
        for src in scraper_sources:
            if not src:
                continue
            url = src.get("url")
            title = src.get("title") or "Exchange Data Source"
            if url and not any(d["url"] == url for d in data_sources):
                data_sources.append({"title": title, "url": url, "type": "exchange"})

        # 5a. Exchange Profile Links (DFM/ADX)
        if ticker != "Unknown":
            if str(exchange).upper() == "DFM":
                dfm_url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}"
                if not any(d["url"] == dfm_url for d in data_sources):
                    data_sources.insert(
                        0,
                        {
                            "title": "DFM Company Profile",
                            "url": dfm_url,
                            "type": "exchange",
                        },
                    )
            elif str(exchange).upper() == "ADX":
                adx_url = f"https://www.adx.ae/en/main-market/company-profile/overview?symbols={ticker}"
                if not any(d["url"] == adx_url for d in data_sources):
                    data_sources.insert(
                        0,
                        {
                            "title": "ADX Company Profile",
                            "url": adx_url,
                            "type": "exchange",
                        },
                    )

        # 6. PDF Results (Metadata)
        for pdf in pdf_results:
            pdf_meta = pdf.get("meta", {})
            if pdf_meta.get("url"):
                url = pdf_meta["url"]
                if not any(d["url"] == url for d in data_sources):
                    data_sources.append(
                        {
                            "title": f"Report: {pdf_meta.get('period', 'Financial Statement')}",
                            "url": url,
                            "type": "pdf",
                        }
                    )

        # Deduplicate by URL
        unique_sources = []
        seen_urls = set()
        for s in data_sources:
            if s["url"] not in seen_urls:
                unique_sources.append(s)
                seen_urls.add(s["url"])

        # 4. Insights Mapping — preserve full rich schema from LLM
        insights = []

        def parse_insight(opt):
            """
            Normalise a raw insight dict into a canonical form.
            Preserves all rich fields (finding, trigger, action, source)
            so the dashboard can render each field separately.
            Falls back gracefully for legacy / plain-text insights.
            """
            if not isinstance(opt, dict):
                return {"category": "Insight", "text": str(opt)}

            # Case-insensitive key lookup
            keys = {k.lower(): v for k, v in opt.items()}

            cat = str(keys.get("category") or keys.get("type") or "Insight")
            finding = str(keys.get("finding") or "")
            trigger = str(keys.get("trigger") or "")
            action = str(keys.get("action") or "")
            source = str(keys.get("source") or "")

            # Legacy / collapsed-text fallback
            text = str(
                keys.get("text") or keys.get("insight") or keys.get("opportunity") or ""
            )

            return {
                "category": cat,
                "finding": finding,
                "trigger": trigger,
                "action": action,
                "source": source,
                # keep text for any legacy renderers that still use it
                "text": action or finding or text or str(opt),
            }

        strategic_opts = final_report.get("Strategic_banking_opportunities", [])
        if isinstance(strategic_opts, list) and strategic_opts:
            for opt in strategic_opts:
                insights.append(parse_insight(opt))
        else:
            # Fallback to top-level insights list (set directly by AnalystAgent)
            raw_insights = state.get("insights", [])
            for opt in raw_insights:
                insights.append(parse_insight(opt))

        # 5. Competitors Mapping
        competitors = []
        comp_data = (enrichments.get("Competitor Analysis") or {}).get("data") or {}
        if "peers" in comp_data:
            for p in comp_data["peers"]:
                competitors.append(
                    {
                        "Company": p.get("Company"),
                        "Mkt Cap": p.get("market_cap"),
                        "P/E": p.get("pe_ratio"),
                        "Rev Growth": p.get("revenue_growth"),
                    }
                )

        # 6. Risks Mapping
        risks = []
        raw_risks = final_report.get("Key_risks_and_considerations", [])
        if isinstance(raw_risks, list):
            for r in raw_risks:
                if isinstance(r, dict):
                    risks.append(
                        {
                            "risk": r.get("risk")
                            or r.get("category")
                            or "Unknown Risk",
                            "consideration": r.get("consideration")
                            or r.get("finding")
                            or "No details available.",
                        }
                    )

        # 7. Final Updates
        updates = {
            "meta": meta,
            "financials": financials,
            "enrichments": enrichments_block,
            "insights": insights,
            "risks": risks,
            "competitors": competitors,
            "chart": chart_data,
            "sources": unique_sources,
            "logs": [
                f"Presentation Agent: Final dashboard structure ready for {self.company_name}"
            ],
            # Keep legacy keys for temporary compatibility if needed
            "financial_data": financial_data,
            "pdf_results": pdf_results,
        }

        return updates

    def _generate_news_summary(self, news_articles: List[Dict]) -> str:
        """Generates a concise LLM summary of the provided news articles."""
        if not news_articles:
            return ""

        # Format articles for the prompt
        articles_str = ""
        for i, art in enumerate(news_articles[:5]):  # use top 5 for summary
            articles_str += f"{i+1}. Title: {art.get('title')}\n   Source: {art.get('source')}\n   Date: {art.get('date')}\n\n"

        prompt = f"""
        You are a highly experienced Financial Analyst and Relationship Manager.
        I will provide you with a list of recent news articles about {self.company_name}.
        
        Your task is to provide a concise, high-level executive summary in bullet points (using - ) that captures the overall sentiment and key developments. 
        Each bullet point should highlight key words or phrases using bold (e.g., **Strategic Growth**).
        Focus on items of strategic importance to a banking Relationship Manager.
        
        News Articles:
        {articles_str}
        
        Executive News Summary (Bulleted list with bold highlights):
        """

        try:
            summary = self.llm_connector.analyze(prompt)
            # Basic cleanup if needed
            return summary.strip()
        except Exception as e:
            self.log(f"Failed to generate news summary: {e}", "WARNING")
            return ""
