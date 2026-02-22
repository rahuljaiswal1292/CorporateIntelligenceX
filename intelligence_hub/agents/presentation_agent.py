import logging
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
        pdf_results = state.get("pdf_results", []) or []

        # 1. Meta Mapping
        meta = {
            "name": self.company_name,
            "description": final_report.get("Executive_summary")
            or enrichments.get("description")
            or financial_data.get("profile", {}).get(
                "description", "No description available."
            ),
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

            unit = fin.get("revenue", {}).get("unit")
            current_metrics = {
                "period": meta_pdf.get("period")
                or meta_pdf.get("report_date")
                or "Latest Report",
                "rev": self._format_currency(
                    fin.get("revenue", {}).get("current"), unit
                ),
                "profit": self._format_currency(
                    fin.get("net_income", {}).get("current"), unit
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

            last_year_metrics = {
                "period": "Previous Year",
                "rev": self._format_currency(
                    fin.get("revenue", {}).get("previous"), unit
                ),
                "profit": self._format_currency(
                    fin.get("net_income", {}).get("previous"), unit
                ),
            }

        # Fallback to daily_summary or scraped data
        daily = financial_data.get("daily_summary", {}).get("data", [])
        if daily and not current_metrics.get("price"):
            latest_day = daily[0]
            current_metrics["price"] = f"AED {latest_day.get('Last', 'N/A')}"
            current_metrics["trend"] = latest_day.get("Change Percentage", "")

        financials = {
            "current": current_metrics,
            "last_year": last_year_metrics,
            "market_cap": enrichments.get("Competitor Analysis", {})
            .get("data", {})
            .get("market_cap")
            or "N/A",
        }

        # 3. Enrichments Mapping
        # News: Rename link -> url, published -> date
        news_articles = []
        raw_articles = enrichments.get("news", {}).get("articles", [])
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
        sources = financial_data.get("sources", [])
        for src in sources:
            if (
                "wikipedia" in src.get("title", "").lower()
                or "wikipedia" in src.get("url", "").lower()
            ):
                wiki_url = src.get("url")
                break
        if not wiki_url:
            wiki_url = enrichments.get("wikipedia", {}).get("url")

        # SERP Count
        serp_count = enrichments.get("_metadata", {}).get("serp_api_calls", 0)

        # DED Mapping
        ded_info = enrichments.get("uae_ded_license") or {}

        enrichments_block = {
            "news": {"sources": news_articles},
            "wikipedia": {"url": wiki_url},
            "serp": {"count": serp_count},
            "ded": ded_info,
        }

        # 4. Insights Mapping (action -> text)
        insights = []
        strategic_opts = final_report.get("Strategic_banking_opportunities", [])
        if isinstance(strategic_opts, list):
            for opt in strategic_opts:
                insights.append(
                    {
                        "category": opt.get("category", "Insight"),
                        "text": opt.get("action") or opt.get("finding") or str(opt),
                    }
                )
        else:
            # Fallback to top-level insights list
            raw_insights = state.get("insights", [])
            for opt in raw_insights:
                insights.append(
                    {
                        "category": opt.get("category", "Insight"),
                        "text": opt.get("action") or opt.get("finding") or str(opt),
                    }
                )

        # 5. Competitors Mapping
        competitors = []
        comp_data = enrichments.get("Competitor Analysis", {}).get("data", {})
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

        # 6. Final Updates
        updates = {
            "meta": meta,
            "financials": financials,
            "enrichments": enrichments_block,
            "insights": insights,
            "competitors": competitors,
            "logs": state.get("logs", [])
            + [
                f"Presentation Agent: Final dashboard structure ready for {self.company_name}"
            ],
            # Keep legacy keys for temporary compatibility if needed
            "financial_data": financial_data,
            "pdf_results": pdf_results,
        }

        return updates
