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
        # This method is required by BaseAgent but we override run()
        # so it might not be called directly if we handle everything in run()
        return {}

    def run(self, state: AgentState) -> Dict:
        """
        Consolidates state into the final UI-ready structure.
        """
        self.company_name = state.get("company_name", "Unknown")
        self.log(f"Formatting final data for {self.company_name}...")

        # 1. Gather Data Sources
        enrichments = state.get("enrichments", {}) or {}
        scraped_data = state.get("financial_data", {}) or {}
        insights = state.get("insights", []) or []
        pdf_results = state.get("pdf_results", []) or []

        # 2. Base Metadata
        # Use Resolved metadata (from MasterAgent/State)
        meta = {
            "query": state.get("query"),
            "ticker": state.get("ticker"),
            "company_name": state.get("company_name"),
            "exchange": state.get("exchange"),
            "website": state.get("website")
            or enrichments.get("website")
            or scraped_data.get("profile", {}).get("website"),
        }

        # 3. Construct Financial Data Structure
        # Start with Scraped Data as base
        final_financial_data = {
            "financials": scraped_data.get("financials", {}),
            "profile": scraped_data.get("profile", {}),
            "sources": scraped_data.get("sources", []),
            "raw_html_snippet": state.get("raw_html", "")
            or scraped_data.get("raw_html_snippet", ""),
        }

        # 4. Enrich Profile (Description, Sector, etc.)
        # MasterAgent enrichments are usually higher quality for description/metadata
        if enrichments.get("description"):
            final_financial_data["profile"]["description"] = enrichments["description"]

        # Add basic meta to profile if missing
        if not final_financial_data["profile"].get("sector") and enrichments.get(
            "industry"
        ):
            final_financial_data["profile"]["sector"] = enrichments["industry"]

        # 5. Add Competitors (from Enrichment)
        # Note: UI components expect 'competitors' key in the root data object
        # OR we can put it in financial_data if we update UI.
        # But for now, we leave it in the top-level state update as well.
        # User requested specific structure for financial_data, but didn't explicitly ask for competitors INSIDE it.
        # However, to be safe and "Display relevant information", I'll ensure it's in the state.

        competitors = []
        if "Competitor Analysis" in enrichments and enrichments[
            "Competitor Analysis"
        ].get("data"):
            comp_data = enrichments["Competitor Analysis"]["data"]
            if "peers" in comp_data:
                # Transform to UI expected format if needed
                # UI expects: Company, Mkt Cap, P/E, Rev Growth
                # MasterAgent output: Company, market_cap, pe_ratio, revenue_growth

                for p in comp_data["peers"]:
                    competitors.append(
                        {
                            "Company": p.get("Company"),
                            "Mkt Cap": p.get("market_cap"),
                            "P/E": p.get("pe_ratio"),
                            "Rev Growth": p.get("revenue_growth"),
                        }
                    )

        # 6. Add News (from Enrichment) -> UI expects 'news'? UI components.py doesn't have render_news currently?
        # Checking components.py... Only render_sources.
        # But mock_data has "news" key.
        # streamlit_app.py doesn't render news explicitly in the main flow list.

        # 7. Merge PDF Results into final_financial_data?
        # User requested structure:
        # { financial_data: { ..., pdf_results: ...? } }
        # The user example didn't show pdf_results in financial_data.
        # But UI renders pdf_analysis from `data["pdf_results"]`.

        # Final State Update
        updates = {
            # Standardized UI Data Block
            "financial_data": final_financial_data,
            # Ensure top-level keys for UI components that look there
            "competitors": competitors,
            # Pass through insights just in case
            "insights": insights,
            # Add logs
            "logs": state.get("logs", [])
            + [f"Presentation Agent: Formatted final data for {self.company_name}"],
        }

        return updates
