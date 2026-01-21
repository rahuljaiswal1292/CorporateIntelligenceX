import logging
from bs4 import BeautifulSoup
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector

logger = logging.getLogger(__name__)

class ADXScraper:
    """
    Scraper for Abu Dhabi Securities Exchange (ADX).
    Handles navigation to 'Financials' tab and table parsing.
    """
    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector
        self.base_url = "https://www.adx.ae"

    def scrape_company(self, ticker: str) -> dict:
        """
        Scrapes ADX for a given company ticker.
        """
        url = f"{self.base_url}/english/market/company/{ticker}"
        logger.info(f"Targeting ADX: {url}")
        
        # Scenario: Mimic clicking 'Financials' tab
        js_scenario = {
            "instructions": [
                {"click": "#tabFinancials"},
                {"wait": 2000}
            ]
        }
        
        html = self.sb.scrape(url, js_scenario=js_scenario)
        if not html:
            return {}
            
        return self._parse_html(html)

    def _parse_html(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        data = {"source": "ADX", "financials": {}}
        
        # 1. Parse Financial Table
        table = soup.select_one(".financials-table table")
        if table:
            rows = table.find_all("tr")
            # Assume Row 1 is header, Row 2 is latest year
            if len(rows) > 1:
                cols = rows[1].find_all("td")
                if len(cols) >= 3:
                    try:
                        # Parsing logic matching the Mock HTML structure
                        rev = cols[1].get_text(strip=True).replace(',', '')
                        profit = cols[2].get_text(strip=True).replace(',', '')
                        
                        data["financials"]["year"] = cols[0].get_text(strip=True)
                        data["financials"]["revenue"] = self._safe_float(rev)
                        data["financials"]["profit"] = self._safe_float(profit)
                    except Exception as e:
                        logger.error(f"Error parsing ADX table: {e}")

        # 2. Parse Profile Info
        sector = soup.select_one("#lblSector")
        if sector:
            data["sector"] = sector.get_text(strip=True)
            
        return data

    def _safe_float(self, val: str) -> float:
        try:
            return float(val)
        except:
            return 0.0
