
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

try:
    from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
    from intelligence_hub.utils.storage_manager import StorageManager
    from intelligence_hub.scrapers.download_manager import DownloadManager
    from intelligence_hub.scrapers.bot_handler import BotHandler
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


try:
    from intelligence_hub.utils.adx_chart_extractor import ADXChartExtractor
except ImportError:
    ADXChartExtractor = None

# StorageManager imported from utils


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
    Advanced Scraper for ADX using direct Playwright automation.
    Handles dynamic content, document downloads, and detailed extration.
    """

    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector
        self.base_url = "https://www.adx.ae"
        self.browser: Optional[Browser] = None
        self.playwright = None
        
        # Initialize enhanced download manager and bot handler
        self.download_manager = DownloadManager(max_age_years=max_age_years) if DownloadManager else None
        self.bot_handler = BotHandler() if BotHandler else None
        
        # known companies map 
        self.known_companies = {
             "FAB": "First Abu Dhabi Bank",
             "FBI": "First Abu Dhabi Bank (Legacy)", # Example mapping
             "CBD": "Commercial Bank of Dubai"
        }

    async def _setup_browser(self):
        """Initialize Playwright browser with stealth settings"""
        logger.info("Initializing Playwright Browser with ENHANCED STEALTH...")
        self.playwright = await async_playwright().start()
        
        # Launch with arguments that mimic a real user session
        self.browser = await self.playwright.chromium.launch(
            headless=config.HEADLESS, # Must be False for best results
            channel="chrome", 
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-extensions",
                "--disable-gpu"
            ]
        )
    
    async def _create_stealth_page(self, context):
        """Create a page with stealth injections"""
        page = await context.new_page()
        
        # Injection 1: Overwrite the `webdriver` property
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Injection 2: Mock Chrome/Plugins
        await page.add_init_script("""
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        return page
    
    async def _teardown_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def scrape_company(self, ticker: str) -> dict:
        """
        Main entry point for scraping a company.
        Executes comprehensive crawl similar to ADXReportCrawler.
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

        try:
            await self._setup_browser()
            
            # Create a context with downloads enabled
            context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Define processing function for each page type
            async def process_page(url, page_type):
                page = await self._create_stealth_page(context)
                
                # Setup page-specific download handler (in 'structured' subfolder)
                page_download_dir = os.path.join(config.DATA_DIR, "adx", ticker, page_type, "structured")
                os.makedirs(page_download_dir, exist_ok=True)
                
                async def handle_download(download):
                    try:
                        suggested_filename = download.suggested_filename
                        path = os.path.join(page_download_dir, suggested_filename)
                        await download.save_as(path)
                        logger.info(f"Downloaded to {page_type}: {path}")
                    except Exception as e:
                        logger.error(f"Download failed in {page_type}: {e}")

                page.on("download", handle_download)
                
                # For orderbook pages, setup chart extractor BEFORE navigation
                chart_extractor = None
                if page_type == "orderbook" and ADXChartExtractor:
                    chart_extractor = ADXChartExtractor()
                    chart_extractor.target_url = url
                    chart_extractor.symbol = chart_extractor._extract_symbol_from_url(url)
                    chart_extractor.target_symbol = chart_extractor.symbol
                    # Attach network listeners BEFORE navigation
                    page.on("request", chart_extractor._handle_request)
                    page.on("response", chart_extractor._handle_response)
                    logger.info(f"Setup chart extractor listeners for {ticker} BEFORE navigation")
                
                logger.info(f"Navigating to {page_type}: {url}")
                try:
                    # Use 'load' for more completeness
                    await page.goto(url, wait_until="load", timeout=90000)
                    
                    # Prepare page (scroll, wait)
                    await self._prepare_page_content(page, page_type)
                    
                    # Extract structured data FIRST for pages that need interaction (like financials)
                    extracted_data = {}
                    if page_type == "overview":
                        extracted_data = await self._extract_overview(page, ticker, page_type)
                    elif page_type == "financials":
                        # This method clicks tabs and triggers data loading
                        extracted_data = await self._interact_and_extract_financials(page, ticker, page_type)
                    elif page_type == "orderbook":
                        # Extract chart data using pre-configured extractor
                        extracted_data = await self._extract_orderbook_chart_with_extractor(page, ticker, url, chart_extractor)
                    elif page_type in ["disclosures", "assembly_meetings", "fundamentals"]:
                        extracted_data = await self._generic_document_extract(page, ticker, page_type)
                    
                    # Capture content AFTER interaction to ensure dynamic data is present
                    content = await page.content()
                    
                    # Save Raw HTML
                    StorageManager.save_page_content(content, "adx", ticker, page_type, "html", "page")

                    # Convert and Store Clean Markdown (using raw HTML for best results)
                    try:
                        md_content = clean_html_to_markdown(content)
                        StorageManager.save_page_content(md_content, "adx", ticker, page_type, "md", "page_clean")
                    except Exception as e:
                        logger.warning(f"Failed to convert/save markdown for {page_type}: {e}")
                        
                    await page.close()
                    return (page_type, extracted_data)
                except Exception as e:
                    logger.error(f"Error processing {page_type}: {e}")
                    await page.close()
                    return (page_type, None)
                    

            # Exec tasks
            tasks = [
                process_page(urls["overview"], "overview"),
                process_page(urls["financials"], "financials"),
                process_page(urls["disclosures"], "disclosures"),
                process_page(urls["shareholders"], "shareholders"),
                process_page(urls["orderbook"], "orderbook"),
                process_page(urls["fundamentals"], "fundamentals"),
                process_page(urls["assembly_meetings"], "assembly_meetings")
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Merge Results
            for page_type, result in results:
                if result:
                    if page_type == "overview":
                        data["profile"] = result.get("profile", {})
                        data["metrics"] = result.get("metrics", {})
                    elif page_type == "financials":
                        data["financials"] = result.get("financials", {})
            
            # Documents are tracked within their respective processing methods if needed
            # Returning merged data without root-level structured/downloads
            return data

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

    async def _prepare_page_content(self, page: Page, page_type: str):
        """Interact with page elements to ensure all content is loaded before capture."""
        # 1. Universal Scroll to trigger lazy loading
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
        except: pass
        
        # 2. Page Specific Waits
        if page_type == "financials":
            try:
                 # Check for bot detection
                 if self.bot_handler and await self.bot_handler.detect_bot_challenge(page):
                     await self.bot_handler.handle_bot_detection(page)
                     
                 # Wait for the tabs or documents to appear
                 logger.info("Waiting for financial data to render...")
                 
                 # Dynamic wait for actual data (PDF links or tables with content)
                 await page.wait_for_function("""
                    () => {
                        const hasReports = !!document.querySelector('a[href*=".pdf"], a[href*="Download"]');
                        const tables = document.querySelectorAll('table, .adx-table, .table-responsive');
                        let tableHasContent = false;
                        for (const tbl of tables) {
                            if (tbl.innerText.replace(/[\u200B-\u200D\uFEFF]/g, '').trim().length > 20) {
                                tableHasContent = true;
                                break;
                            }
                        }
                        return hasReports || tableHasContent;
                    }
                 """, timeout=30000)
                 await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Wait timeout on financials: {e}")
        
        elif page_type == "shareholders":
            logger.info("Waiting for shareholders data mapping...")
            try:
                # Wait for any of the common shareholder tables or headings
                await page.wait_for_selector(".adx-shareholders-board, .shareholders-board_content, h2", timeout=15000)
                await page.wait_for_timeout(2000)
            except: pass
            
        elif page_type == "overview":
            logger.info("Waiting for overview details...")
            try:
                # Wait for share capital or auditor sections if they appear late
                await page.wait_for_selector(".sharecard-title, .companyoverview-pra, h3", timeout=15000)
                await page.wait_for_timeout(2000)
            except: pass
            
    async def _extract_orderbook_chart_with_extractor(self, page: Page, ticker: str, url: str, extractor: 'ADXChartExtractor') -> dict:
        """
        Extract chart data from orderbook page using a pre-configured ADXChartExtractor.
        The extractor should already have network listeners attached BEFORE page navigation.
        This extracts OHLCV (Open, High, Low, Close, Volume) data and saves it to CSV.
        """
        logger.info(f"Extracting orderbook chart data for {ticker} with pre-configured extractor...")
        
        if not extractor:
            logger.warning("ADXChartExtractor not available, skipping chart extraction")
            return {"chart_extracted": False, "reason": "ADXChartExtractor not available"}
        
        try:
            # The extractor already has listeners attached and has been capturing network traffic
            # Now we just need to trigger interactions and process the captured data
            
            logger.info("Waiting for chart content to load...")
            await page.wait_for_timeout(2000)
            
            # Scroll to bring the chart into view
            await page.evaluate("window.scrollTo(0, 800)")
            await asyncio.sleep(3)
            
            # Try to trigger 3-month history via interaction
            await extractor._trigger_3month_history(page)
            
            # If we discovered the API, fetch 3 months (100 records)
            if extractor.discovered_api_url:
                logger.info(f"Using discovered API: {extractor.discovered_api_url}")
                
                # Ensure full_url is constructed safely
                full_url = extractor.discovered_api_url
                if "recordCount=" not in full_url:
                    if "?" in full_url:
                        full_url += "&recordCount=100"
                    else:
                        full_url += "?recordCount=100"
                
                logger.info(f"Fetching 3-month data via request context: {full_url}")
                try:
                    response = await page.context.request.get(full_url, headers=extractor.request_headers)
                    if response.ok:
                        history_json = await response.json()
                        results = history_json.get("response", {}).get("results", [])
                        if results:
                            logger.info(f"Successfully captured {len(results)} historical records.")
                            extractor.captured_data = [] # Reset to use full history
                            extractor._normalize_list_data(results)
                    else:
                        logger.error(f"Request context fetch failed: {response.status} {response.status_text}")
                except Exception as e:
                    logger.error(f"Failed to fetch history via request context: {e}")

            # If still no data, check for page-level scripts (NEXT_DATA)
            if not extractor.captured_data:
                logger.info("Checking __NEXT_DATA__ for embedded chart data...")
                next_data = await page.evaluate("() => JSON.stringify(window.__NEXT_DATA__ || {})")
                if next_data:
                    try:
                        extractor._handle_json_content(json.loads(next_data), "NEXT_DATA")
                    except: pass

            if not extractor.captured_data:
                logger.warning("No chart data captured. Waiting a bit more...")
                await asyncio.sleep(5)

            # Final processing
            if extractor.captured_data:
                extractor._process_data()
                extractor._save_to_csv()
                logger.info(f"Successfully extracted {len(extractor.processed_df)} chart data points for {ticker}")
                return {
                    "chart_extracted": True,
                    "records_count": len(extractor.processed_df),
                    "date_range": {
                        "start": str(extractor.processed_df['Date'].min()),
                        "end": str(extractor.processed_df['Date'].max())
                    }
                }
            else:
                logger.warning(f"No chart data extracted for {ticker}")
                return {"chart_extracted": False, "reason": "No data captured"}
                
        except Exception as e:
            logger.error(f"Error extracting orderbook chart data: {e}")
            import traceback
            traceback.print_exc()
            return {"chart_extracted": False, "reason": str(e)}
            
    def _clean_generic_adx_content(self, html_content: str) -> str:
        """Remove generic ADX noise with maximum prejudice."""
        if not html_content: return ""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Broad Removal of known noise containers
            noise_selectors = [
                ".marqueeWrapperTicker", ".ticker-value",
                ".uae-current-date", ".language-switcher", ".accessbility-container",
                ".login-btn", ".mw-btn", "header", "footer", ".adx-header", ".adx-footer",
                ".search-btn-responsive", ".side-bar", ".sidebar", ".breadcrumb",
                "nav", ".navbar", ".adx-top-nav", ".social-links", ".cookie-banner",
                "#top-nav", ".sub-footer"
            ]
            for selector in noise_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # 2. Targeted Removal of ticker-specific lists (using find_all for robustness)
            for ul in soup.find_all("ul", attrs={"aria-label": "tickerValue"}):
                ul.decompose()
            
            # 3. Heuristic: Remove items containing multiple common ADX tickers (noise lists)
            ticker_keywords = ["2POINTZERO", "ADAVIATION", "ADNOCGAS", "LULU", "FAB", "ADCB", "ALDAR", "IHC", "EAND", "ADIB"]
            pattern = re.compile("|".join(ticker_keywords))
            
            for item in soup.find_all(["li", "tr", "div"]):
                # If a small container contains multiple tickers, it's noise
                txt = item.get_text()
                if 2 < len(txt) < 300:
                    matches = pattern.findall(txt)
                    if len(set(matches)) >= 2: # At least 2 different noise tickers
                        item.decompose()

            return str(soup)
        except Exception as e:
            logger.warning(f"Error cleaning ADX content: {e}")
            return html_content

    async def _interact_and_extract_financials(self, page: Page, ticker: str, page_type: str) -> dict:
        """
        Interact with financial page to download all English documents.
        Enhanced with DownloadManager for reliable downloads with retry, validation, and date filtering.
        """
        logger.info(f"Interacting with Financials page for {ticker}...")
        
        # Check for bot detection
        if self.bot_handler and await self.bot_handler.detect_bot_challenge(page):
            await self.bot_handler.handle_bot_detection(page, severity='medium')
        
        # 1. Click on Report Type buttons to load different sections
        # We try to prioritize 'Annual' as it usually has the most data
        try:
            # Look for tab buttons
            tab_selectors = [
                'button:has-text("Annual")', 
                '.adx-tab_item:has-text("Annual")',
                'button:has-text("Yearly")',
                'a[role="tab"]:has-text("Annual")'
            ]
            
            clicked_any = False
            for selector in tab_selectors:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    logger.info(f"Clicking specific tab: {await btn.inner_text()}")
                    await btn.click()
                    clicked_any = True
                    break
            
            if not clicked_any:
                # Fallback to general tab buttons
                buttons = await page.locator('button, a[role="tab"]').filter(has_text=re.compile(r'annual|yearly|quarterly|interim', re.IGNORECASE)).all()
                for btn in buttons[:1]: # Just click the first one if not clicked yet
                    if await btn.is_visible():
                        await btn.click()
                        clicked_any = True

            if clicked_any:
                await page.wait_for_timeout(3000)
                await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            logger.warning(f"Error navigating tabs: {e}")

        # Ensure we wait for the table to be visible after clicking
        try:
            await page.wait_for_selector(".adx-table, table", timeout=10000)
        except: pass

        # 2. Find all document links (PDF and Office formats)
        document_links = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'];
            return links
                .filter(a => {
                    const href = a.href.toLowerCase();
                    return docFormats.some(fmt => href.includes(fmt)) || 
                           href.includes('download') || 
                           href.includes('cdn') ||
                           href.includes('apigateway');
                })
                .map((a, index) => ({
                    url: a.href,
                    text: a.textContent.trim(),
                    title: a.title || a.getAttribute('aria-label') || '',
                    index: index
                }));
        }''')
        
        logger.info(f"Found {len(document_links)} potential document links.")
        
        # 3. Filter for English documents
        english_docs = []
        for doc in document_links:
            text_combined = f"{doc['text']} {doc['title']} {doc['url']}".upper()
            
            # Exclude Arabic documents
            if any(ar in text_combined for ar in ['AR', 'ARABIC', 'عربي', '_AR.', '/AR/', 'AR-AE']):
                logger.info(f"Skipping Arabic document: {doc['text'][:50]}")
                continue
            
            # Check for Arabic unicode in text
            if any('\u0600' <= char <= '\u06FF' for char in doc['text']):
                continue
            
            # Determine expected file type
            url_lower = doc['url'].lower()
            if '.pdf' in url_lower:
                doc['expected_type'] = 'pdf'
            elif '.xlsx' in url_lower or '.xls' in url_lower:
                doc['expected_type'] = 'xlsx' if '.xlsx' in url_lower else 'xls'
            elif '.docx' in url_lower or '.doc' in url_lower:
                doc['expected_type'] = 'docx' if '.docx' in url_lower else 'doc'
            else:
                doc['expected_type'] = 'pdf'  # default
            
            english_docs.append(doc)
        
        logger.info(f"Filtered to {len(english_docs)} English documents.")
        
        # 4. Download documents using enhanced DownloadManager
        downloaded_count = 0
        failed_downloads = []
        skipped_old = []
        
        # Directory for all files
        target_dir = os.path.join(config.DATA_DIR, "adx", ticker, page_type, "structured")
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Target directory: {target_dir}")
        
        # Use DownloadManager if available, otherwise fallback to old method
        if self.download_manager:
            logger.info("Using enhanced DownloadManager with parallel downloads")
            
            results = await self.download_manager.download_batch_parallel(
                page=page,
                documents=english_docs[:50],  # Process up to 50 documents
                target_dir=target_dir,
                max_concurrent=10,  # 10 concurrent downloads
                max_retries=3
            )
            
            # Count successful downloads
            downloaded_count = sum(1 for r in results if r is not None)
            failed_downloads = [doc for doc, result in zip(english_docs[:50], results) if result is None]
            
            # Get statistics
            stats = self.download_manager.get_stats()
            logger.info(f"\n{'='*60}")
            logger.info(f"Download Statistics:")
            logger.info(f"  Attempted: {stats['attempted']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped (old): {stats['skipped_old']}")
            logger.info(f"  Skipped (invalid): {stats['skipped_invalid']}")
            logger.info(f"{'='*60}\n")
            
        else:
            # Fallback to old method if DownloadManager not available
            logger.warning("DownloadManager not available, using fallback method")
            # ... (keep old code as fallback)
        
        return {
            "financials": {
                "documents_found": len(english_docs),
                "documents_downloaded": downloaded_count,
                "documents_failed": len(failed_downloads),
                "download_stats": self.download_manager.get_stats() if self.download_manager else {}
            }
        }



    async def _generic_document_extract(self, page: Page, ticker: str, page_type: str) -> dict:
        """
        Generic document extraction for ADX pages (disclosures, assembly meetings, fundamentals).
        Enhanced with DownloadManager for reliable downloads with retry, validation, and date filtering.
        """
        logger.info(f"Starting generic document extraction for {page_type}...")
        
        # Check for bot detection
        if self.bot_handler and await self.bot_handler.detect_bot_challenge(page):
            await self.bot_handler.handle_bot_detection(page, severity='low')
        
        # 1. Find all document links
        document_links = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'];
            return links
                .filter(a => {
                    const href = a.href.toLowerCase();
                    const text = (a.textContent || "").toLowerCase();
                    
                    // Include if has document format extension
                    if (docFormats.some(fmt => href.includes(fmt))) return true;
                    
                    // Include if has download indicators
                    if (href.includes('download') || href.includes('cdn') || href.includes('apigateway')) return true;
                    
                    // Include if text suggests it's a document
                    if (text.includes('download') || text.includes('pdf') || text.includes('report')) return true;
                    
                    return false;
                })
                .map((a, index) => ({
                    url: a.href,
                    text: a.textContent.trim(),
                    title: a.title || a.getAttribute('aria-label') || '',
                    index: index
                }));
        }''')
        
        logger.info(f"Found {len(document_links)} potential document links on {page_type} page.")
        
        # 2. Filter for English documents and determine expected type
        english_docs = []
        for doc in document_links:
            text_combined = f"{doc['text']} {doc['title']} {doc['url']}".upper()
            
            # Exclude Arabic documents
            if any(ar in text_combined for ar in ['AR', 'ARABIC', 'عربي', '_AR.', '/AR/', 'AR-AE']):
                continue
            
            # Check for Arabic unicode range in text
            if any('\u0600' <= char <= '\u06FF' for char in doc['text']):
                continue
            
            # Determine expected file type
            url_lower = doc['url'].lower()
            if '.pdf' in url_lower:
                doc['expected_type'] = 'pdf'
            elif '.xlsx' in url_lower:
                doc['expected_type'] = 'xlsx'
            elif '.xls' in url_lower:
                doc['expected_type'] = 'xls'
            elif '.csv' in url_lower:
                doc['expected_type'] = 'csv'
            elif '.docx' in url_lower:
                doc['expected_type'] = 'docx'
            elif '.doc' in url_lower:
                doc['expected_type'] = 'doc'
            else:
                doc['expected_type'] = 'pdf'  # default
            
            english_docs.append(doc)
        
        logger.info(f"Filtered to {len(english_docs)} English documents.")
        
        # 3. Download documents using enhanced DownloadManager
        downloaded_count = 0
        failed_downloads = []
        
        target_dir = os.path.join(config.DATA_DIR, "adx", ticker, page_type, "structured")
        os.makedirs(target_dir, exist_ok=True)
        logger.info(f"Target directory: {target_dir}")
        
        downloaded_files_list = []
        
        # Use DownloadManager if available
        if self.download_manager:
            logger.info("Using enhanced DownloadManager with parallel downloads")
            
            # Use parallel batch download
            results = await self.download_manager.download_batch_parallel(
                page=page,
                documents=english_docs[:50],  # Process up to 50 documents
                target_dir=target_dir,
                max_concurrent=10,
                max_retries=3
            )
            
            # Collect successful downloads
            downloaded_files_list = [r for r in results if r is not None]
            downloaded_count = len(downloaded_files_list)
            failed_downloads = [doc for doc, result in zip(english_docs[:50], results) if result is None]
            
            # Get statistics
            stats = self.download_manager.get_stats()
            logger.info(f"\n{'='*60}")
            logger.info(f"Download Statistics for {page_type}:")
            logger.info(f"  Attempted: {stats['attempted']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped (old): {stats['skipped_old']}")
            logger.info(f"  Skipped (invalid): {stats['skipped_invalid']}")
            logger.info(f"{'='*60}\n")
            
        else:
            # Fallback to old method
            logger.warning("DownloadManager not available, using fallback method")
            # ... (keep old code as fallback)

        return {
            "documents_found": len(english_docs),
            "documents_downloaded": downloaded_count,
            "documents_failed": len(failed_downloads),
            "page_type": page_type,
            "files": downloaded_files_list,
            "download_stats": self.download_manager.get_stats() if self.download_manager else {}
        }

    async def _extract_disclosures(self, page: Page, ticker: str, page_type: str) -> dict:
        # Deprecated - use _generic_document_extract instead
        return {}

    async def search_ticker(self, query: str) -> tuple:
        return None, None

# Run Standalone
if __name__ == "__main__":
    tickers  = [
        # 'LULU', 
        # 'ADNOCGAS',
        # 'EAND',
        # 'ADNHC',
        'ALDAR',
        # 'FAB',
        # 'ALPHADATA'
        ]
    for ticker in tickers:
        async def main():
            scraper = ADXScraper()
            # Test with verified ticker
            await scraper.scrape_company(ticker)

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
