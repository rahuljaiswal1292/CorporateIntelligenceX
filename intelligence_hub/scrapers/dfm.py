import logging
from bs4 import BeautifulSoup
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector

logger = logging.getLogger(__name__)

from datetime import datetime
from intelligence_hub.utils.storage_manager import StorageManager

class DFMScraper:
    """
    Scraper for Dubai Financial Market (DFM).
    Handles parsing of DFM's specific report structure.
    """
    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector
        self.base_url = "https://www.dfm.ae"

    async def scrape_company(self, ticker: str) -> dict:
        """
        Scrapes DFM for a given company ticker using specific URL patterns.
        """
        base_profile_url = f"https://www.dfm.ae/the-exchange/market-information//company/{ticker}/profile"
        reports_url = f"https://www.dfm.ae/the-exchange/market-information//company/{ticker}/reports"
        news_url = f"https://www.dfm.ae/the-exchange/market-information//company/{ticker}/news-disclosures"
        
        logger.info(f"Targeting DFM for {ticker}...")
        
        data = {
            "source": "DFM", 
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "news": []
        }

        # Parallel Fetch
        import asyncio
        logger.info(f"Fetching DFM data in parallel for {ticker}...")
        
        results = await asyncio.gather(
            self.sb.scrape_async(base_profile_url),
            self.sb.scrape_async(reports_url),
            self.sb.scrape_async(news_url)
        )
        html_profile, html_reports, html_news = results

        # 1. Profile
        if html_profile:
            data["profile"] = self._parse_profile(html_profile)
        else:
            logger.warning(f"DFM: Failed to fetch profile for {ticker}")

        # 2. Reports (Financials)
        if html_reports:
            data["financials"] = self._parse_financials(html_reports)
        
        # 3. News
        # if html_news and hasattr(self, '_parse_news'):
        #    data["news"] = self._parse_news(html_news)

        # Save Structured
        StorageManager.save_structured(data, "dfm", ticker)
            
        return data

    async def search_ticker(self, query: str) -> tuple:
        """
        Searches DFM for a company name and returns (ticker, name).
        Returns (None, None) if not found.
        """
        logger.info(f"Searching DFM for '{query}'...")
        # Placeholder for real URL: e.g. https://www.dfm.ae/search?k=...
        return None, None

    def _parse_profile(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "listing_date": "NOT AVAILABLE",
            "isin": "NOT AVAILABLE",
            "website": "NOT AVAILABLE",
            "board_members": []
        }
        
        # Example Selectors (Generic - would need adjustment based on actual HTML)
        name_tag = soup.select_one("h1.company-name")
        if name_tag:
            profile["company_name"] = name_tag.get_text(strip=True)
            
        # Meta info often in a dl/dt/dd list or table
        for row in soup.select(".company-info-row"):
            label = row.select_one(".label")
            val = row.select_one(".value")
            if label and val:
                lbl_text = label.get_text(strip=True).lower()
                val_text = val.get_text(strip=True)
                
                if "sector" in lbl_text:
                    profile["sector"] = val_text
                elif "listing date" in lbl_text:
                    profile["listing_date"] = val_text
                elif "isin" in lbl_text:
                    profile["isin"] = val_text
                elif "website" in lbl_text:
                    profile["website"] = val_text

        return profile

    def _parse_financials(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        financials = {
            "year": "NOT AVAILABLE",
            "revenue": "NOT AVAILABLE",
            "net_profit": "NOT AVAILABLE",
            "eps": "NOT AVAILABLE",
            "assets": "NOT AVAILABLE"
        }
        
        # Look for financial summary table
        # Attempting generic table parsing
        table = soup.select_one("table.financials-summary")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    lbl = cols[0].get_text(strip=True).lower()
                    val = cols[1].get_text(strip=True)
                    
                    if "revenue" in lbl:
                        financials["revenue"] = val
                    elif "profit" in lbl:
                        financials["net_profit"] = val
                    elif "assets" in lbl:
                        financials["assets"] = val
                        
        return financials

    def _parse_viz_str(self, val: str) -> float:
        """Parses strings like '26.7B' into float."""
        if not val or val == "NOT AVAILABLE":
            return 0.0
        val = val.upper().replace('AED', '').strip()
        mult = 1.0
        if 'B' in val:
            mult = 1_000_000_000
            val = val.replace('B', '')
        elif 'M' in val:
            mult = 1_000_000
            val = val.replace('M', '')
            
        try:
            return float(val) * mult
        except:
            return 0.0
