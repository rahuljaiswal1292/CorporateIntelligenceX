import logging
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector
from intelligence_hub.scrapers.adx import ADXScraper
from intelligence_hub.scrapers.dfm import DFMScraper
from intelligence_hub.scrapers.web import WebScraper

logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    """
    Agent 2: The Scraper Orchestrator.
    Routes the request to the correct site-specific scraper.
    """
    def __init__(self):
        self.sb = ScrapingBeeConnector()
        self.adx = ADXScraper(self.sb)
        self.dfm = DFMScraper(self.sb)
        self.web = WebScraper(self.sb)

    def run(self, state: AgentState) -> AgentState:
        ticker = state["ticker"]
        exchange = state["exchange"]
        logger.info(f"Orchestrator: Scraping {ticker} on {exchange}...")
        
        logs = state.get("logs", [])
        logs.append(f"Starting Deep Scrape for {ticker} on {exchange}...")
        
        data = {}
        
        if exchange == "ADX":
            data = self.adx.scrape_company(ticker)
        elif exchange == "DFM":
            data = self.dfm.scrape_company(ticker)
        else:
            # Fallback to web search if URL exists (Mock for now)
            if state.get("website"):
                data = self.web.scrape_site(state["website"])
        
        logs.append("Scraping complete. Financials extracted.")
        
        return {
            "financial_data": data.get("financials", {}),
            "doc_urls": [data.get("pdf_url")] if data.get("pdf_url") else [],
            "logs": logs
        }
