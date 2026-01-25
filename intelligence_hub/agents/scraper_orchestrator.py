import logging
import json
from intelligence_hub.scrapers.adx import ADXScraper
from intelligence_hub.scrapers.dfm import DFMScraper
from intelligence_hub.scrapers.wiki import WikiScraper
from intelligence_hub.scrapers.yahoo import YahooFinanceScraper
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector
from intelligence_hub.connectors.pinecone_client import PineconeConnector

logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    """
    Orchestrates the scraping process:
    1. Checks Vector DB for fresh data.
    2. If stale/missing, routes to specific scrapers (ADX, DFM, Yahoo, Wiki).
    3. Aggregates results.
    """
    def __init__(self):
        self.sb_connector = ScrapingBeeConnector()
        self.db = PineconeConnector()
        
        self.adx_scraper = ADXScraper(self.sb_connector)
        self.dfm_scraper = DFMScraper(self.sb_connector)
        self.wiki_scraper = WikiScraper(self.sb_connector)
        self.yahoo_scraper = YahooFinanceScraper(self.sb_connector)

    import traceback
    from intelligence_hub.graph.state import AgentState

    def run(self, state: AgentState) -> AgentState:
        """
        LangGraph Entry Point.
        """
        logger.info("Scraper: Received request...")
        logs = state.get("logs", [])
        
        ticker = state.get("ticker")
        exchange = state.get("exchange", "ADX") # Default to ADX if unknown
        company_name = state.get("company_name", "Unknown")
        
        try:
            # Sync wrapper call
            data = self.scrape_data(ticker, exchange, company_name)
            logs.append(f"Scraper: Fetched data for {ticker} from {exchange} & Sources.")
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            logs.append(f"Scraper: Error fetching data - {str(e)}")
            data = {}
            
        return {
            "financial_data": data,
            "logs": logs,
            # Pass through
            "ticker": ticker,
            "company_name": company_name
        }

    def scrape_data(self, ticker: str, exchange: str, company_name: str) -> dict:
        """
        Synchronous wrapper for parallel data acquisition.
        """
        import asyncio
        import nest_asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            nest_asyncio.apply()
            return loop.run_until_complete(self._scrape_data_parallel(ticker, exchange, company_name))
        else:
            return loop.run_until_complete(self._scrape_data_parallel(ticker, exchange, company_name))

    async def _scrape_data_parallel(self, ticker: str, exchange: str, company_name: str) -> dict:
        """
        Internal async entry point for data acquisition. Parallelizes extraction.
        """
        import asyncio
        logger.info(f"Orchestrating PARALLEL data fetch for {ticker} ({exchange})...")
        
        # 1. Check Cache
        is_stale = self.db.check_staleness(ticker)
        if not is_stale:
            cached_data = self.db.fetch_cached_financials(ticker)
            if cached_data:
                logger.info(f"Returning cached data for {ticker}")
                return cached_data

        # 2. Scrape Fresh Data (Parallel Agents)
        scraped_data = {
            "financials": {}, 
            "profile": {}, 
            "sources": []
        }
        
        # If loop is running, get it. If not, we are inside run_until_complete so it is running.
        loop = asyncio.get_running_loop()
        tasks = []

        # Task A: Exchange Scraper
        if exchange == "ADX":
            tasks.append(self.adx_scraper.scrape_company(ticker))
        elif exchange == "DFM":
            tasks.append(self.dfm_scraper.scrape_company(ticker))
        else:
            async def no_op(): return {}
            tasks.append(no_op())

        # Task B: Yahoo Finance (Sync -> Async)
        if ticker and ticker != "UNKNOWN":
            tasks.append(loop.run_in_executor(None, self.yahoo_scraper.scrape_ticker, ticker))
        else:
             async def no_op_y(): return {}
             tasks.append(no_op_y())
             
        # Task C: Wikipedia (Sync -> Async)
        tasks.append(loop.run_in_executor(None, self.wiki_scraper.scrape_profile, company_name))
        
        # Execute Parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Unpack
        primary_data = results[0] if not isinstance(results[0], Exception) else {}
        yf_data = results[1] if not isinstance(results[1], Exception) else {}
        wiki_data = results[2] if not isinstance(results[2], Exception) else {}
        
        # Log Exceptions
        for i, res in enumerate(results):
             if isinstance(res, Exception):
                 logger.error(f"Task {i} failed: {res}")

        # 3. Aggregate Results
        
        # A. Exchange Data
        if primary_data.get("financials"):
            scraped_data["financials"] = primary_data["financials"]
            scraped_data["sources"].append({"title": f"{exchange} Filing", "url": primary_data.get("url", exchange)})
        
        # B. Yahoo Data
        if yf_data:
             scraped_data["sources"].append({"title": "Yahoo Finance", "url": yf_data.get("url")})
        
        # C. Wiki Data
        if wiki_data:
             scraped_data["sources"].append({"title": "Wikipedia", "url": wiki_data.get("url")})
             scraped_data["profile"] = {"description": "Retrieved from Wikipedia"} 
             scraped_data["raw_html_snippet"] = wiki_data.get("raw_html_snippet") 

        # 4. Index Fresh Data to Pinecone (Persist)
        self.db.upsert_financials(ticker, scraped_data)
        
        return scraped_data
