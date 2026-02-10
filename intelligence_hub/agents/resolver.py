import logging
import asyncio
from intelligence_hub.graph.state import AgentState
from intelligence_hub.config.settings import config
from intelligence_hub.connectors.pinecone_client import PineconeConnector
from intelligence_hub.utils.web_search import WebSearch
from intelligence_hub.connectors.playwright_scraper import PlaywrightConnector
try:
    import nest_asyncio
except ImportError:
    nest_asyncio = None

logger = logging.getLogger(__name__)

class ResolverAgent:
    """
    Agent 1: The Resolver.
    Maps user query to Entity, Ticker, and Exchange using Dynamic Web Search.
    Orchestrates scraping via Playwright.
    """
    def run(self, state: AgentState) -> AgentState:
        query = state["query"]
        logger.info(f"Resolver: Resolving '{query}'...")
        logs = state.get("logs", [])
        
        # 1. Web Search for Identity (Exchange, Wiki, Official)
        logs.append(f"Resolver: Searching web for '{query}' identity...")
        links = WebSearch.find_company_links(query)
        
        exchange_url = links.get("exchange_url")
        exchange_name = links.get("exchange_name", "Unknown")
        ticker = links.get("ticker_hint")
        wiki_url = links.get("wiki_url")
        official_url = links.get("official_url")
        
        if exchange_url:
             logs.append(f"Resolver: Found Exchange URL: {exchange_url} ({exchange_name})")
        if wiki_url:
             logs.append(f"Resolver: Found Wiki URL: {wiki_url}")

        # 2. Scrape Data (Playwright)
        scraper = PlaywrightConnector()
        
        # Initialize Data Containers with Defaults
        profile_data = {"description": "", "sector": "", "website": official_url or "", "est_date": "", "shareholders": []}
        financial_data = {"financials": {}, "risk": {}, "sources": []}
        
        async def scrape_all():
             tasks = []
             if wiki_url:
                 tasks.append(scraper.scrape_wiki_profile(wiki_url))
             if exchange_url:
                 tasks.append(scraper.scrape_exchange_data(exchange_url, exchange_name))
                 
             if not tasks:
                 return []
                 
             results = await asyncio.gather(*tasks, return_exceptions=True)
             return results

        # Run Async Scraping (Sync Wrapper)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                if nest_asyncio:
                    nest_asyncio.apply()
                scraped_results = loop.run_until_complete(scrape_all())
            else:
                scraped_results = asyncio.run(scrape_all())
                
            # Process Results
            for res in scraped_results:
                if isinstance(res, dict):
                    if "description" in res: # Wiki Profile result
                        profile_data.update(res)
                    elif "financials" in res: # Exchange Data result
                        financial_data = res
                    # If 'risk', 'sources' were top-level keys in scraper return, handle them
                            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            logs.append(f"Resolver: Scraping error: {e}")

        # 3. Construct Final State
        final_ticker = ticker if ticker else "UNKNOWN"
        if final_ticker == "UNKNOWN":
             # Try to extract ticker from exchange URL again or just use query
             final_ticker = query.upper().replace(" ", "")

        # Prepare unified financial data structure for UI
        unified_data = {
            "profile": profile_data,
            "financials": financial_data.get("financials", {}),
            "risk": financial_data.get("risk", {}),
            "sources": financial_data.get("sources", []),
            "meta": {
                "name": query.title(),
                "description": profile_data.get("description", ""),
                "sector": profile_data.get("sector", ""),
                "website": profile_data.get("website", official_url),
                "exchange": exchange_name,
                "ticker": final_ticker,
                "est_date": profile_data.get("est_date", ""),
                "shareholders": profile_data.get("shareholders", [])
            }
        }
        
        # Pass this as 'financial_data' (which stream/UI expects)
        
        return {
            "ticker": final_ticker, 
            "company_name": query.title(), 
            "exchange": exchange_name,
            "financial_data": unified_data,
            "logs": logs + [f"Resolved '{query}' to {final_ticker} ({exchange_name}) via Web Search & Playwright."]
        }
