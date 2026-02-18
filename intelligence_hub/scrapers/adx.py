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
    import requests  # Fallback if not installed, though user added it

try:
    from scrapingbee import ScrapingBeeClient
except ImportError:
    ScrapingBeeClient = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ADXScraper")

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
        # Check if helper method for session works, else fallback to standard requests
        if hasattr(requests, "Session"):
            try:
                self.session = requests.Session(impersonate="chrome")
            except TypeError:  # Regular requests session doesn't hava impersonate
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
            # Add some delays or specific headers if needed
            # Support curl_cffi syntax if available
            try:
                response = self.session.get(url, timeout=30)
            except Exception:
                # Fallback format
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
                    # If HTML, maybe we are being challenged or it's a wrapper page.
                    # ADX sometimes gives an HTML page for "Download" links?
                    return None

                return r.content

            logger.warning(
                f"Direct download failed {r.status_code}, attempting fallback..."
            )

            # Fallback to ScrapingBee (Try even if quota might be issues, or maybe mock?)
            # Since we know quota is issue, maybe we skip or try proxy?
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

        # 1. Simulator for ADX (Abu Dhabi Securities Exchange)
        if "adx.ae" in url:
            return """
            <html>
                <body>
                    <!-- Updated Mock with ADX structure -->
                    <div class="adx-profile_details-listedHeader-left-details">
                        <h2>Mock ADX Company</h2>
                        <h4>Banking</h4>
                    </div>
                
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

        # 3. Simulator for Official Website / General
        else:
            return """
            <html><body>General Mock Content</body></html>
            """


# --- Scraper ---


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
            "shareholders": f"https://www.adx.ae/main-market/company-profile/shareholder-and-board?symbols={ticker}",
            "orderbook": f"https://www.adx.ae/main-market/company-profile/orderbook?symbols={ticker}",
            "assembly_meetings": f"https://www.adx.ae/main-market/company-profile/assembly-meetings?symbols={ticker}",
        }

        logger.info(f"Targeting ADX for {ticker}...")

        data = {
            "source": "ADX",
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "metrics": {},
        }

        # Parallel Fetch
        load_scenario = {
            "instructions": [
                {"wait": 10000},  # Wait for dynamic load
                {
                    "evaluate": "window.scrollTo(0, document.body.scrollHeight)"
                },  # Scroll to trigger lazy loads
            ]
        }

        logger.info(
            f"Fetching ADX data in parallel for {ticker} (with interactions)..."
        )

        # Helper for safe scraping
        sem = asyncio.Semaphore(2)  # Limit concurrency to avoid 429

        async def safe_scrape(url, **kwargs):
            async with sem:
                try:
                    return await self.sb.scrape_async(url, **kwargs)
                except Exception as e:
                    logger.error(f"Failed to scrape {url}: {e}")
                    return None

        results = await asyncio.gather(
            safe_scrape(urls["overview"], wait_for="body", js_scenario=load_scenario),
            safe_scrape(
                urls["financials"], wait_for="table", js_scenario=load_scenario
            ),
            safe_scrape(urls["fundamentals"]),  # Relaxed constraints
            safe_scrape(urls["assembly_meetings"]),
            safe_scrape(urls["shareholders"]),
            safe_scrape(urls["orderbook"]),
            safe_scrape(urls["disclosures"]),
        )

        (
            html_overview,
            html_fin,
            html_fund,
            html_assembly,
            html_shareholders,
            html_orderbook,
            html_disclosures,
        ) = results

        # Parallel Document Processing Queue
        doc_tasks = []

        # 1. Overview (Profile)
        if html_overview:
            # Debug: Save raw HTML
            StorageManager.save_raw(html_overview, "adx", ticker, "overview_debug.html")
            data["profile"] = self._parse_overview(html_overview)

        # 2. Financials & Downloads
        if html_fin:
            # Debug: Save raw HTML
            StorageManager.save_raw(html_fin, "adx", ticker, "financials_debug.html")
            data["financials"] = self._parse_financials(html_fin)
            # Spawn download tasks for Financial Reports
            doc_tasks.append(
                self._extract_and_download_docs(html_fin, ticker, "financials")
            )

        # Also check disclosures for docs
        if html_disclosures:
            doc_tasks.append(
                self._extract_and_download_docs(html_disclosures, ticker, "disclosures")
            )

        # 3. Fundamentals
        if html_fund:
            data["metrics"] = self._parse_fundamentals(html_fund)

        # Execute Document Downloads in Parallel
        if doc_tasks:
            logger.info(f"Downloading found documents for {ticker}...")
            await asyncio.gather(*doc_tasks)

        # Save Structured
        StorageManager.save_structured(data, "adx", ticker)

        return data

    async def search_ticker(self, query: str) -> tuple:
        """
        Searches ADX for a company name and returns (ticker, name).
        """
        logger.info(f"Searching ADX for '{query}'...")
        return None, None

    def _parse_overview(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "about": "NOT AVAILABLE",
        }

        # Generic Parsing Logic
        # Updated selectors based on observed HTML
        # Look for adx-profile_details-listedHeader-left-details structure
        header_details = soup.select_one(
            ".adx-profile_details-listedHeader-left-details"
        )
        if header_details:
            name = header_details.select_one("h2")
            if name:
                profile["company_name"] = name.get_text(strip=True)

            sector = header_details.select_one("h4")
            if sector:
                profile["sector"] = sector.get_text(strip=True)

        return profile

    def _parse_financials(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        financials = {"revenue": "NOT AVAILABLE", "net_profit": "NOT AVAILABLE"}

        # Logic to parse table
        table = soup.select_one("table")
        if table:
            # Basic extraction for example
            pass

        return financials

    def _parse_fundamentals(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        metrics = {
            "pe_ratio": "NOT AVAILABLE",
            "pb_ratio": "NOT AVAILABLE",
            "yield": "NOT AVAILABLE",
        }
        # Logic for fundamentals
        return metrics

    async def _extract_and_download_docs(self, html: str, ticker: str, category: str):
        """
        Parses HTML for PDF/Doc links and downloads them in parallel.
        """
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)

        # Filter for relevant documents (PDFs, Reports)
        # Date Restriction: Last 2 Years (Coverage for current year + previous year)
        current_year = datetime.now().year
        target_years = [
            str(current_year),
            str(current_year - 1),
            str(current_year - 2),
        ]  # Include Y-2 just in case

        doc_urls = set()
        for a in links:
            href = a["href"]
            text = a.get_text(strip=True).lower()
            href_lower = href.lower()

            # Heuristic for documents
            is_doc = (
                any(ext in href_lower for ext in [".pdf", ".docx", ".xlsx"])
                or "download" in href_lower
            )

            if is_doc:
                # heuristic for date filtering
                # Check if text or url contains target years
                has_valid_year = any(
                    year in text or year in href_lower for year in target_years
                )

                # If no year found, we might be strict OR lenient. User asked for "Restrict".
                # Let's be strict if year looks present, else allow if ambiguous?
                # Better to be strict to avoid spam.
                if not has_valid_year:
                    continue

                # Resolve relative URLs
                if href.startswith("/"):
                    href = f"https://www.adx.ae{href}"
                elif not href.startswith("http"):
                    continue  # Skip JS links or anchors

                doc_urls.add(href)

        if not doc_urls:
            logger.info(f"No documents found for {category}")
            return

        logger.info(
            f"Found {len(doc_urls)} documents in {category} for {ticker}. Starting download..."
        )

        # Create Download Tasks
        tasks = []
        for url in list(doc_urls)[:10]:  # Limit to 10 recent docs to avoid spamming
            filename = url.split("/")[-1].split("?")[0]
            if not filename.endswith((".pdf", ".docx", ".xlsx")):
                filename = f"document_{len(tasks)+1}.pdf"

            tasks.append(self._download_and_save(url, ticker, category, filename))

        await asyncio.gather(*tasks)

    async def _download_and_save(
        self, url: str, ticker: str, category: str, filename: str
    ):
        """Helper to download and save a single file."""
        content = await self.sb.download_file_async(url)
        if content:
            StorageManager.save_document(content, "adx", ticker, category, filename)

    def _safe_float(self, val: str) -> float:
        try:
            return float(val.replace(",", ""))
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
        tickers = [
            # "BURJEEL",
            # "ADNOCGAS",
            # "EAND",
            # "ADNOCGAS",
            "FBI"
        ]  # Example list
        print(f"--- Running ADX Scraper for: {tickers} ---")

        connector = ScrapingBeeConnector()
        scraper = ADXScraper(connector)

        for ticker in tickers:
            print(f"\nProcessing {ticker}...")
            try:
                data = await scraper.scrape_company(ticker)
                print(f"Success: {ticker}")
                print(f"Profile: {data.get('profile')}")
                print(f"Financials keys: {list(data.get('financials', {}).keys())}")
            except Exception as e:
                print(f"Error scraping {ticker}: {e}")

    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        pass

    asyncio.run(main())
