import os
import logging
import requests
from scrapingbee import ScrapingBeeClient
from typing import Optional, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScrapingBeeConnector:
    """
    Robust connector for ScrapingBee with built-in Mock Mode.
    Allows the agent to function even without active API keys by simulating responses.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SCRAPINGBEE_API_KEY")
        if self.api_key:
            self.client = ScrapingBeeClient(api_key=self.api_key)
            self.mode = "LIVE"
        else:
            self.client = None
            self.mode = "MOCK"
            logger.warning("SCRAPINGBEE_API_KEY not found. Running in MOCK MODE.")

    def scrape(self, url: str, render_js: bool = True, wait_for: str = None, js_scenario: dict = None) -> str:
        """
        Scrapes a URL.
        
        Args:
            url (str): The URL to scrape.
            render_js (bool): Whether to use a headless browser to render JS.
            wait_for (str): CSS selector to wait for before returning.
            js_scenario (dict): ScrapingBee JS scenario instructions.
            
        Returns:
            str: The HTML content of the page (or mock HTML).
        """
        logger.info(f"[{self.mode}] Scraping URL: {url}")
        
        if self.mode == "LIVE":
            return self._scrape_live(url, render_js, wait_for, js_scenario)
        else:
            return self._scrape_mock(url)

    def _scrape_live(self, url: str, render_js: bool, wait_for: str, js_scenario: dict) -> str:
        """Executes actual API call to ScrapingBee."""
        try:
            params = {
                "render_js": render_js,
            }
            if wait_for:
                params["wait_for"] = wait_for
            if js_scenario:
                params["js_scenario"] = js_scenario
                
            response = self.client.get(url, params=params)
            
            if response.status_code == 200:
                return response.content.decode("utf-8")
            else:
                logger.error(f"ScrapingBee Error {response.status_code}: {response.content}")
                return ""
        except Exception as e:
            logger.error(f"ScrapingBee Exception: {str(e)}")
            return ""

    def _scrape_mock(self, url: str) -> str:
        """Returns detailed Mock HTML based on the URL pattern to simulate real scraping."""
        
        # 1. Simulator for ADX (Abu Dhabi Securities Exchange)
        if "adx.ae" in url:
            return """
            <html>
                <body>
                    <h1>Abu Dhabi Securities Exchange</h1>
                    <div class="financials-table">
                        <table>
                            <thead>
                                <tr><th>Period</th><th>Revenue (AED)</th><th>Net Profit (AED)</th><th>EPS</th></tr>
                            </thead>
                            <tbody>
                                <tr><td>2023</td><td>43,000,000,000</td><td>21,500,000,000</td><td>3.2</td></tr>
                                <tr><td>2022</td><td>39,500,000,000</td><td>18,000,000,000</td><td>2.8</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="company-profile">
                        <span id="lblSector">Banking</span>
                        <span id="lblListingDate">16/10/2007</span>
                    </div>
                </body>
            </html>
            """
            
        # 2. Simulator for DFM (Dubai Financial Market)
        elif "dfm.ae" in url:
            return """
            <html>
                <body>
                    <h1>Dubai Financial Market</h1>
                    <div class="financial-reports">
                        <div class="row">
                            <span class="label">Revenue 2023:</span> <span class="val">26.7B</span>
                        </div>
                        <div class="row">
                            <span class="label">Net Profit 2023:</span> <span class="val">11.6B</span>
                        </div>
                    </div>
                    <a href="https://www.dfm.ae/reports/annual_2023.pdf" class="download-link">Annual Report 2023</a>
                </body>
            </html>
            """
            
        # 3. Simulator for Official Website / General
        else:
            return """
            <html>
                <body>
                    <h1>Investor Relations</h1>
                    <p>We are a leading banking institution in the MENA region.</p>
                    <table>
                        <tr><td>Metric</td><td>Value</td></tr>
                        <tr><td>Total Assets</td><td>860 Billion AED</td></tr>
                        <tr><td>Customer Deposits</td><td>600 Billion AED</td></tr>
                    </table>
                </body>
            </html>
            """
