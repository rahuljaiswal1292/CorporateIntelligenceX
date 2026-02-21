import logging
import json
from intelligence_hub.scrapers.scrapingbee import ScrapingBeeConnector
from intelligence_hub.utils.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class YahooFinanceScraper:
    """
    Scraper for Yahoo Finance.
    Used as fallback for Price/Financials if Exchange sites fail.
    """

    def __init__(self, connector: WebScraperConnector):
        self.connector = connector
        self.base_url = "https://finance.yahoo.com/quote"

    def scrape_ticker(self, ticker: str, exchange_suffix: str = ".AE") -> dict:
        """
        Scrapes Yahoo Finance for a specific ticker (e.g. EMAAR.AE).
        """
        full_ticker = f"{ticker}{exchange_suffix}"
        url = f"{self.base_url}/{full_ticker}"

        logger.info(f"YF: Scraping {full_ticker}...")
        html = self.connector.scrape(url)

        if not html:
            return {}

        # Save Raw
        StorageManager.save_raw(html, "yahoo", full_ticker)

        # Parse (Simple heuristic extraction or LLM-based)
        # For simplicity in this demo, we assume extraction logic here or pass HTML to Analyst
        # Returning a raw-ish dict for the Orchestrator to process

        data = {
            "source": "Yahoo Finance",
            "url": url,
            "raw_html_snippet": html[:5000],  # Truncated for meta
        }

        StorageManager.save_structured(data, "yahoo", full_ticker)
        return data
