import logging
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
            if unit and "thousand" in unit.lower():
                val_float *= 1000

            if val_float >= 1_000_000_000:
                return f"AED {val_float / 1_000_000_000:.1f}B"
            elif val_float >= 1_000_000:
                return f"AED {val_float / 1_000_000:.1f}M"
            else:
                return f"AED {val_float:,.0f}"
        except:
            return str(value)

    def run(self, state: AgentState) -> Dict:
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
        financial_data = state.get("financial_data", {}) or {}
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
            # pdf_results is sorted newest first by PdfAgent
            latest_pdf = pdf_results[0]
            fin = latest_pdf.get("financials", {})
            meta_pdf = latest_pdf.get("meta", {})

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
            }
            # Add ratios if available in PDF (newly implemented or parsed)
            for ratio in [
                "roe",
                "roa",
                "npl_ratio",
                "capital_adequacy",
                "cost_to_income",
                "liquidity_coverage_ratio",
            ]:
                if ratio in fin:
                    current_metrics[ratio] = fin[ratio]

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
                    "dates": [d["Date"] for d in sorted_daily],
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
        comp_data_block = competitor_analysis.get("data") or {}

        financials = {
            "current": current_metrics,
            "last_year": last_year_metrics,
            "market_cap": comp_data_block.get("market_cap") or "N/A",
        }

        # 3. Enrichments Mapping
        # News: Rename link -> url, published -> date
        news_articles = []
        news_block = enrichments.get("news") or {}
        raw_articles = news_block.get("articles", [])
        for art in raw_articles:
            news_articles.append(
                {
                    "title": art.get("title"),
                    "url": art.get("link"),
                    "source": art.get("source"),
                    "date": art.get("published"),
                }
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
            wiki_url = (enrichments.get("wikipedia") or {}).get("url")

        # SERP Count
        meta_block = enrichments.get("_metadata") or {}
        serp_count = meta_block.get("serp_api_calls", 0)

        # DED Mapping
        ded_info = enrichments.get("uae_ded_license") or {}

        enrichments_block = {
            "news": {"sources": news_articles},
            "wikipedia": {"url": wiki_url},
            "serp": {"count": serp_count},
            "ded": ded_info,
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

        # 4. Insights Mapping (action -> text)
        insights = []

        # Helper to extract category/text with synonyms and case-insensitivity
        def parse_insight(opt):
            if not isinstance(opt, dict):
                return {"category": "Insight", "text": str(opt)}

            # Case-insensitive key lookup
            keys = {k.lower(): v for k, v in opt.items()}

            cat = keys.get("category") or keys.get("type") or "Insight"

            # Text synonyms: action, finding, opportunity, text
            txt = (
                keys.get("action")
                or keys.get("finding")
                or keys.get("opportunity")
                or keys.get("text")
                or str(opt)
            )

            return {"category": str(cat), "text": str(txt)}

        strategic_opts = final_report.get("Strategic_banking_opportunities", [])
        if isinstance(strategic_opts, list):
            for opt in strategic_opts:
                insights.append(parse_insight(opt))
        else:
            # Fallback to top-level insights list
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
