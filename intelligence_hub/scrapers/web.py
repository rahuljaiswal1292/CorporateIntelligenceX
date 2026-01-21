import logging
from bs4 import BeautifulSoup
from intelligence_hub.connectors.scrapingbee import ScrapingBeeConnector

logger = logging.getLogger(__name__)

class WebScraper:
    """
    Generic Web Scraper for official company websites.
    """
    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector

    def scrape_site(self, url: str) -> dict:
        logger.info(f"Targeting Website: {url}")
        html = self.sb.scrape(url)
        return self._parse_html(html)

    def _parse_html(self, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        data = {"source": "WEB", "attributes": {}}
        
        # Simple simulation: Extract first table on page
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    data["attributes"][key] = val
        return data
