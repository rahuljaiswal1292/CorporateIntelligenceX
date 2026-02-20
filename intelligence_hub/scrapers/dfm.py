import logging
import asyncio
import os
import json
import logging
from typing import Optional, Dict
from datetime import datetime
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Use curl_cffi for requests to bypass Cloudflare
try:
    from curl_cffi import requests
except ImportError:
    import requests  # Fallback if not installed

try:
    from scrapingbee import ScrapingBeeClient
except ImportError:
    ScrapingBeeClient = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DFMScraper")

# --- Configuration & Storage ---


class Config:
    SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")
    # Use centralized DATA_DIRECTORY
    from intelligence_hub.config.config import DATA_DIRECTORY

    DATA_DIR = DATA_DIRECTORY


config = Config()


class StorageManager:
    """
    Manages file storage for scraped data in structured/unstructured formats.
    Structure: ./data/{source}/{format}/{ticker}_{timestamp}.{ext}
    """

    @staticmethod
    def save_raw(
        content: str, source: str, ticker: str, extension: str = "html"
    ) -> str:
        """
        Saves raw content (Unstructured).
        """
        directory = os.path.join(config.DATA_DIR, source, "unstructured")
        os.makedirs(directory, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}.{extension}"
        filepath = os.path.join(directory, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved raw data to {filepath}")
        return filepath

    @staticmethod
    def save_document(
        content: bytes, source: str, ticker: str, category: str, filename: str
    ) -> str:
        """
        Saves a downloaded document (PDF, DOCX, etc.) to a categorized folder.
        Structure: ./data/{source}/{ticker}/{category}/{filename}
        """
        # Santize filename
        filename = "".join(
            [
                c
                for c in filename
                if c.isalpha() or c.isdigit() or c in (" ", ".", "_", "-")
            ]
        ).rstrip()

        directory = os.path.join(config.DATA_DIR, source, ticker, category)
        os.makedirs(directory, exist_ok=True)

        filepath = os.path.join(directory, filename)

        with open(filepath, "wb") as f:
            f.write(content)

        logger.info(f"Saved document to {filepath}")
        return filepath

    @staticmethod
    def save_structured(data: dict, source: str, ticker: str) -> str:
        """
        Saves parsed data (Structured JSON).
        """
        directory = os.path.join(config.DATA_DIR, source, "structured")
        os.makedirs(directory, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}.json"
        filepath = os.path.join(directory, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved structured data to {filepath}")
        return filepath


# --- Connector ---


class ScrapingBeeConnector:
    """
    Robust connector for ScrapingBee with built-in Mock Mode.
    Allows the agent to function even without active API keys by simulating responses.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.SCRAPINGBEE_API_KEY
        if self.api_key and ScrapingBeeClient:
            try:
                self.client = ScrapingBeeClient(api_key=self.api_key)
                self.mode = "LIVE"
            except Exception as e:
                logger.error(f"Failed to initialize ScrapingBeeClient: {e}")
                self.mode = "MOCK"
        else:
            self.client = None
            self.mode = "MOCK"
            if not self.api_key:
                logger.warning("SCRAPINGBEE_API_KEY not found. Running in MOCK MODE.")

        # Session for direct fallback (using curl_cffi to bypass Cloudflare)
        if hasattr(requests, "Session"):
            try:
                self.session = requests.Session(impersonate="chrome")
            except TypeError:
                self.session = requests.Session()
                self.session.headers.update(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
        else:
            import requests as std_requests

            self.session = std_requests.Session()

    async def scrape_async(
        self,
        url: str,
        render_js: bool = True,
        wait_for: str = None,
        js_scenario: dict = None,
    ) -> str:
        """
        Asynchronously scrapes a URL using run_in_executor.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return await loop.run_in_executor(
            None, self.scrape, url, render_js, wait_for, js_scenario
        )

    def scrape(
        self,
        url: str,
        render_js: bool = True,
        wait_for: str = None,
        js_scenario: dict = None,
    ) -> str:
        """
        Scrapes a URL.
        """
        logger.info(f"[{self.mode}] Scraping URL: {url}")

        if self.mode == "LIVE":
            return self._scrape_live(url, render_js, wait_for, js_scenario)
        else:
            return self._scrape_mock(url)

    def _scrape_live(
        self, url: str, render_js: bool, wait_for: str, js_scenario: dict
    ) -> str:
        """Executes actual API call to ScrapingBee with fallback to Direct."""
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

            logger.error(
                f"ScrapingBee Error {response.status_code}: {response.content}"
            )

            # Fallback for 401 (Quota) or other errors
            if response.status_code in [401, 403, 429, 500]:
                logger.info("Switching to Direct Scraping Fallback...")
                return self._scrape_direct(url)

            return ""
        except Exception as e:
            logger.error(f"ScrapingBee Exception: {str(e)}")
            logger.info("Exception occurred, trying Direct Scraping Fallback...")
            return self._scrape_direct(url)

    def _scrape_direct(self, url: str) -> str:
        """Direct scraping using requests session."""
        try:
            logger.info(f"[DIRECT] Scraping URL: {url}")
            try:
                response = self.session.get(url, timeout=30)
            except Exception:
                response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                return response.text
            logger.error(
                f"Direct Scraping Failed {response.status_code}: {response.text[:500]}"
            )
            return ""
        except Exception as e:
            logger.error(f"Direct Scraping Exception: {e}")
            return ""

    async def download_file_async(self, url: str) -> bytes:
        """
        Asynchronously downloads a file (PDF/Doc) using run_in_executor.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.download_file, url)

    def download_file(self, url: str) -> bytes:
        """
        Downloads a file (binary) handling potential redirects or ScrapingBee wrapper.
        """
        logger.info(f"[{self.mode}] Downloading File: {url}")

        if self.mode == "MOCK":
            # Return a minimally VALID PDF binary
            return (
                b"%PDF-1.4\n"
                b"1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
                b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
                b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/MediaBox [0 0 595.28 841.89]\n/Contents 5 0 R\n>>\nendobj\n"
                b"4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/Name /F1\n/BaseFont /Helvetica\n>>\nendobj\n"
                b"5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n70 700 Td\n/F1 24 Tf\n(Mock PDF from CorporateIntelligenceX) Tj\nET\nendstream\nendobj\n"
                b"xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000111 00000 n\n0000000212 00000 n\n0000000301 00000 n\n"
                b"trailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n392\n%%EOF\n"
            )

        try:
            # Try direct download first with session
            r = self.session.get(url, timeout=60, stream=True)

            if r.status_code == 200:
                # Validate Content-Type
                ctype = r.headers.get("Content-Type", "").lower()
                if "html" in ctype or "text" in ctype:
                    logger.warning(
                        f"Download returned HTML instead of binary ({ctype}). Likely blocked or login required."
                    )
                    return None

                return r.content

            logger.warning(
                f"Direct download failed {r.status_code}, attempting fallback..."
            )

            # Fallback to ScrapingBee (Try even if quota might be issues, or maybe mock?)
            if self.mode == "LIVE":
                logger.info("Fallback: Downloading via ScrapingBee...")
                params = {"render_js": False}
                response = self.client.get(url, params=params)

                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(
                        f"ScrapingBee Fallback Error {response.status_code}: {response.content}"
                    )
                    return None

            return None
        except Exception as e:
            logger.error(f"Download Exception: {str(e)}")
            return None

    def _scrape_mock(self, url: str) -> str:
        """Returns detailed Mock HTML based on the URL pattern to simulate real scraping."""

        # 1. Simulator for ADX
        if "adx.ae" in url:
            return """
            <html><body><h1>Mock ADX</h1></body></html>
            """

        # 2. Simulator for DFM (Dubai Financial Market)
        elif "dfm.ae" in url:
            return """
            <html>
                <body>
                    <!-- Profile Section -->
                    <div class="company-header">
                        <h1 class="company-name">Mock Company PJSC</h1>
                    </div>
                    
                    <div class="company-info">
                        <div class="company-info-row">
                            <span class="label">Sector</span>
                            <span class="value">Banking</span>
                        </div>
                    </div>

                    <!-- Financials Section -->
                    <div class="financials-section">
                        <h2>Financial Summary</h2>
                        <table class="financials-summary">
                            <thead>
                                <tr><td>Indicator</td><td>Value (AED)</td></tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Revenue (TTM)</td>
                                    <td>26,700,000,000</td>
                                </tr>
                                <tr>
                                    <td>Net Profit</td>
                                    <td>11,600,000,000</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- Reports Section -->
                    <div class="reports-section">
                        <a href="/docs/annual-report-2023.pdf">Annual Report 2023</a>
                    </div>
                </body>
            </html>
            """
        else:
            return "<html><body>Mock Content</body></html>"


# --- Scraper ---


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
        base_profile_url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}/profile"
        reports_url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}/reports"
        news_url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}/news-disclosures"

        logger.info(f"Targeting DFM for {ticker}...")

        data = {
            "source": "DFM",
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "news": [],
        }

        # Parallel Fetch
        logger.info(f"Fetching DFM data in parallel for {ticker}...")

        results = await asyncio.gather(
            self.sb.scrape_async(base_profile_url),
            self.sb.scrape_async(reports_url),
            self.sb.scrape_async(news_url),
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
        """
        logger.info(f"Searching DFM for '{query}'...")
        # Mock Search Logic for robustness
        q = query.lower()
        if "ajman" in q:
            return "AJMANBANK", "Ajman Bank"
        if "dubai islamic" in q or "dib" in q:
            return "DIB", "Dubai Islamic Bank"
        return None, None

    def _parse_profile(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "listing_date": "NOT AVAILABLE",
            "isin": "NOT AVAILABLE",
            "website": "NOT AVAILABLE",
            "board_members": [],
        }

        # Example Selectors
        name_tag = soup.select_one("h1.company-name")
        if name_tag:
            profile["company_name"] = name_tag.get_text(strip=True)

        # Meta info
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
        soup = BeautifulSoup(html, "html.parser")
        financials = {
            "year": "NOT AVAILABLE",
            "revenue": "NOT AVAILABLE",
            "net_profit": "NOT AVAILABLE",
            "eps": "NOT AVAILABLE",
            "assets": "NOT AVAILABLE",
        }

        # Look for financial summary table
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
        val = val.upper().replace("AED", "").strip()
        mult = 1.0
        if "B" in val:
            mult = 1_000_000_000
            val = val.replace("B", "")
        elif "M" in val:
            mult = 1_000_000
            val = val.replace("M", "")

        try:
            return float(val) * mult
        except:
            return 0.0


if __name__ == "__main__":
    # Standalone Execution / Validation
    # Load dotenv if available locally
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    async def main():
        tickers = ["EMAAR", "ENBD", "DEWA", "AJMANBANK"]
        print(f"--- Running DFM Scraper for: {tickers} ---")

        connector = ScrapingBeeConnector()
        scraper = DFMScraper(connector)

        for ticker in tickers:
            print(f"\nProcessing {ticker}...")
            try:
                data = await scraper.scrape_company(ticker)
                print(f"Success: {ticker}")
                print(f"Profile: {data.get('profile')}")
                print(f"Financials: {data.get('financials')}")
            except Exception as e:
                print(f"Error scraping {ticker}: {e}")

    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
