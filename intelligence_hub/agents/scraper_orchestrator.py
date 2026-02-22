import logging
import asyncio
import json
import sys
from typing import Dict, List, Any, Optional

from intelligence_hub.scrapers.adx import ADXScraper
from intelligence_hub.scrapers.dfm import DFMScraper
from intelligence_hub.scrapers.wiki import WikiScraper
from intelligence_hub.scrapers.yahoo import YahooFinanceScraper
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from intelligence_hub.graph.state import AgentState

logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """
    Orchestrates the scraping process:
    1. Checks Vector DB for fresh data (optional).
    2. Routes to specific scrapers (ADX, DFM, Yahoo, Wiki).
    3. Aggregates and persists results.
    """

    def __init__(self):
        self.db = CorporateProfileStore()

        self.adx_scraper = ADXScraper()
        self.dfm_scraper = DFMScraper()
        self.wiki_scraper = WikiScraper()
        self.yahoo_scraper = YahooFinanceScraper()

    def run(self, state: AgentState) -> AgentState:
        """
        LangGraph Entry Point.
        """
        logger.info("Scraper: Received request...")
        logs = []

        ticker = state.get("ticker")
        exchange = (
            state.get("exchange") or "UNKNOWN"
        )  # Don't default to ADX — could be DFM
        company_name = state.get("company_name", "Unknown")

        try:
            # Sync wrapper call to run async scraping
            data = self.scrape_data(ticker, exchange, company_name)
            logs.append(
                f"Scraper: Fetched data for {ticker} from {exchange} & Sources."
            )
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            import traceback

            traceback.print_exc()
            logs.append(f"Scraper: Error fetching data - {str(e)}")
            data = {}

        # Extract metadata for state
        doc_urls = [s.get("url") for s in data.get("sources", []) if s.get("url")]
        raw_html = data.get("raw_html_snippet", "")

        return {
            "financial_data": data,
            "doc_urls": doc_urls,
            "raw_html": raw_html,
            "logs": logs,
        }

    def scrape_data(self, ticker: str, exchange: str, company_name: str) -> dict:
        """
        Synchronous wrapper for parallel data acquisition.
        Handles event loop policy for Windows/Playwright compatibility.
        """
        import nest_asyncio

        # Enforce Windows Proactor policy for Playwright subprocesses
        if sys.platform == "win32":
            try:
                from asyncio import WindowsProactorEventLoopPolicy

                # We check the policy itself or the loop's selector if possible,
                # but standard practice is to set it at the start.
                if not isinstance(
                    asyncio.get_event_loop_policy(), WindowsProactorEventLoopPolicy
                ):
                    asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
            except ImportError:
                pass

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            nest_asyncio.apply()
            return loop.run_until_complete(
                self._scrape_data_parallel(ticker, exchange, company_name)
            )
        else:
            return loop.run_until_complete(
                self._scrape_data_parallel(ticker, exchange, company_name)
            )

    async def _scrape_data_parallel(
        self, ticker: str, exchange: str, company_name: str
    ) -> dict:
        """
        Internal async entry point for data acquisition. Parallelizes extraction.
        """
        logger.info(f"Orchestrating PARALLEL data fetch for {ticker} ({exchange})...")

        # 1. Scrape Fresh Data (Parallel Agents)
        scraped_data = {"financials": {}, "profile": {}, "sources": [], "documents": []}

        loop = asyncio.get_running_loop()
        tasks = []

        # Task A: Exchange Scraper (Only if Ticker and Exchange are known)
        exchange_upper = str(exchange).upper() if exchange else "UNKNOWN"
        if ticker and ticker != "UNKNOWN" and exchange_upper in ["ADX", "DFM"]:
            if exchange_upper == "ADX":
                logger.info(f"Scraper: Routing to ADX for {ticker}")
                tasks.append(self.adx_scraper.scrape_company(ticker))
            elif exchange_upper == "DFM":
                logger.info(f"Scraper: Routing to DFM for {ticker}")
                tasks.append(self.dfm_scraper.scrape_company(ticker))
        else:
            logger.info(
                f"Scraper: No specific exchange scraper for {ticker} ({exchange})"
            )

            async def no_op():
                return {}

            tasks.append(no_op())

        # Task B: Yahoo Finance (Sync -> Async)
        if ticker and ticker != "UNKNOWN":
            tasks.append(
                loop.run_in_executor(None, self.yahoo_scraper.scrape_ticker, ticker)
            )
        else:

            async def no_op_y():
                return {}

            tasks.append(no_op_y())

        # Task C: Wikipedia (Sync -> Async)
        tasks.append(
            loop.run_in_executor(None, self.wiki_scraper.scrape_profile, company_name)
        )

        # Execute Parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Unpack results safely
        primary_data = (
            results[0]
            if len(results) > 0 and not isinstance(results[0], Exception)
            else {}
        )
        yf_data = (
            results[1]
            if len(results) > 1 and not isinstance(results[1], Exception)
            else {}
        )
        wiki_data = (
            results[2]
            if len(results) > 2 and not isinstance(results[2], Exception)
            else {}
        )

        # Log Exceptions
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Scraper Task {i} failed: {res}")

        # 2. Aggregate Results

        # A. Exchange Data
        if primary_data:
            if "financials" in primary_data:
                scraped_data["financials"] = primary_data["financials"]

            # Add sources from primary scraper
            scraped_data["sources"].append(
                {
                    "title": f"{exchange_upper} Filing Data",
                    "url": primary_data.get("url", f"{exchange_upper} Link"),
                }
            )
            # Add documents if available
            if "documents" in primary_data:
                scraped_data["documents"] = primary_data["documents"]

            # Add profile if available
            if "profile" in primary_data:
                scraped_data["profile"].update(primary_data["profile"])

        # B. Yahoo Data
        if yf_data:
            scraped_data["sources"].append(
                {
                    "title": "Yahoo Finance",
                    "url": yf_data.get("url", "https://finance.yahoo.com"),
                }
            )
            if isinstance(yf_data, dict):
                # Update visuals/metrics if needed
                pass

        # C. Wiki Data
        if wiki_data:
            scraped_data["sources"].append(
                {"title": "Wikipedia", "url": wiki_data.get("url", "#")}
            )
            scraped_data["profile"]["description"] = wiki_data.get(
                "summary", "Retrieved from Wikipedia"
            )
            scraped_data["raw_html_snippet"] = wiki_data.get("raw_html_snippet", "")

        # 3. Persist Fresh Data to Local Store (Vector DB / JSON)
        try:
            self.db.store_financials(ticker, scraped_data)
        except Exception as e:
            logger.warning(f"Failed to persist scraped data to store: {e}")

        return scraped_data
