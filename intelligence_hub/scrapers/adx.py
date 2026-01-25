import logging
from bs4 import BeautifulSoup
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector

logger = logging.getLogger(__name__)

from datetime import datetime
from intelligence_hub.utils.storage_manager import StorageManager

class ADXScraper:
    """
    Scraper for Abu Dhabi Securities Exchange (ADX).
    Handles navigation to 'Financials' tab and table parsing.
    """
    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector
        self.base_url = "https://www.adx.ae"

    async def scrape_company(self, ticker: str) -> dict:
        """
        Scrapes ADX for a given company ticker using specific URL patterns.
        """
        urls = {
            "overview": f"https://www.adx.ae/main-market/company-profile/overview?symbols={ticker}",
            "financials": f"https://www.adx.ae/main-market/company-profile/financial-reports?symbols={ticker}",
            "disclosures": f"https://www.adx.ae/main-market/company-profile/disclosures?symbols={ticker}",
            "fundamentals": f"https://www.adx.ae/main-market/company-profile/fundamentals?symbols={ticker}",
        }
        
        logger.info(f"Targeting ADX for {ticker}...")
        
        data = {
            "source": "ADX", 
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "metrics": {}
        }
        
        # Parallel Fetch
        import asyncio
        
        logger.info(f"Fetching ADX data in parallel for {ticker}...")
        results = await asyncio.gather(
            self.sb.scrape_async(urls["overview"]),
            self.sb.scrape_async(urls["financials"]),
            self.sb.scrape_async(urls["fundamentals"])
        )
        
        html_overview, html_fin, html_fund = results

        # 1. Overview (Profile)
        if html_overview:
            data["profile"] = self._parse_overview(html_overview)

        # 2. Financials
        if html_fin:
            data["financials"] = self._parse_financials(html_fin)

        # 3. Fundamentals
        if html_fund:
            data["metrics"] = self._parse_fundamentals(html_fund)

        # Save Structured
        StorageManager.save_structured(data, "adx", ticker)
              
        return data

    async def search_ticker(self, query: str) -> tuple:
        """
        Searches ADX for a company name and returns (ticker, name).
        Returns (None, None) if not found.
        """
        # Placeholder for real search implementation.
        # Check https://www.adx.ae/search endpoint or similar.
        logger.info(f"Searching ADX for '{query}'...")
        # For verification purposes, we'll allow this to be mocked.
        return None, None

    def _parse_overview(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE", 
            "about": "NOT AVAILABLE"
        }
        
        # Generic Parsing Logic
        name = soup.select_one(".company-title")
        if name:
            profile["company_name"] = name.get_text(strip=True)
            
        sector = soup.select_one(".sector-label")
        if sector:
            profile["sector"] = sector.get_text(strip=True)
            
        return profile

    def _parse_financials(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        financials = {
            "revenue": "NOT AVAILABLE",
            "net_profit": "NOT AVAILABLE"
        }
        
        # Logic to parse table
        table = soup.select_one("table")
        if table:
             # Basic extraction for example
             pass
             
        return financials
        
    def _parse_fundamentals(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        metrics = {
            "pe_ratio": "NOT AVAILABLE",
            "pb_ratio": "NOT AVAILABLE", 
            "yield": "NOT AVAILABLE"
        }
        
        # Logic for fundamentals
        return metrics

    def _safe_float(self, val: str) -> float:
        try:
            return float(val.replace(',', ''))
        except:
            return 0.0
