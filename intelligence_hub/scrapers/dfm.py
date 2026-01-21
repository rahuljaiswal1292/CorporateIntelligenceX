import logging
from bs4 import BeautifulSoup
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector

logger = logging.getLogger(__name__)

class DFMScraper:
    """
    Scraper for Dubai Financial Market (DFM).
    Handles parsing of DFM's specific report structure.
    """
    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector
        self.base_url = "https://www.dfm.ae"

    def scrape_company(self, ticker: str) -> dict:
        url = f"{self.base_url}/en/issuers/listed-securities/{ticker}"
        logger.info(f"Targeting DFM: {url}")
        
        html = self.sb.scrape(url)
        return self._parse_html(html)

    def _parse_html(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        data = {"source": "DFM", "financials": {}}
        
        # Parsing logic for Mock DFM HTML
        # Look for .row with .label 'Revenue 2023:'
        rows = soup.select(".financial-reports .row")
        for row in rows:
            label = row.select_one(".label")
            val = row.select_one(".val")
            
            if label and val:
                lbl_text = label.get_text(strip=True).lower()
                val_text = val.get_text(strip=True)
                
                if "revenue" in lbl_text:
                    data["financials"]["revenue_str"] = val_text
                    data["financials"]["revenue"] = self._parse_viz_str(val_text)
                elif "net profit" in lbl_text:
                    data["financials"]["profit_str"] = val_text
                    data["financials"]["profit"] = self._parse_viz_str(val_text)

        # Look for annual report link
        link = soup.select_one("a.download-link")
        if link:
            data["pdf_url"] = link['href']
            
        return data

    def _parse_viz_str(self, val: str) -> float:
        """Parses strings like '26.7B' into float."""
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
