
import logging
import asyncio
import os
import json
import re
import time
from typing import Optional, Dict, List
from datetime import datetime
from urllib.parse import urljoin

# Third-party imports
from bs4 import BeautifulSoup

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

try:
    from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
    from intelligence_hub.utils.storage_manager import StorageManager
    from intelligence_hub.utils.date_extractor import DateExtractor
    from intelligence_hub.scrapers.download_manager import DownloadManager
    from intelligence_hub.scrapers.bot_handler import BotHandler
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
    Scraper for Dubai Financial Market (DFM) using direct Playwright automation.
    Handles dynamic content, document downloads, and detailed extraction.
    """

    def __init__(self, connector: ScrapingBeeConnector):
        self.sb = connector
        self.base_url = "https://www.dfm.ae"
        self.browser: Optional[Browser] = None
        self.playwright = None
        
        # Initialize enhanced download manager and bot handler
        self.download_manager = DownloadManager(max_age_years=3)
        self.downloaded_texts = set()  # Track downloaded items by text/content
        self.downloaded_urls = set()   # Track downloaded items by URL to avoid duplicates
        self.expanded_views = set()   # Track which views have been expanded
        self.bot_handler = BotHandler() if BotHandler else None

    async def _setup_browser(self):
        """Initialize Playwright browser with stealth settings"""
        logger.info("Initializing Playwright Browser with ENHANCED STEALTH for DFM...")
        self.playwright = await async_playwright().start()
        
        # Launch with arguments that mimic a real user session
        self.browser = await self.playwright.chromium.launch(
            headless=getattr(config, 'HEADLESS', False), 
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
        Scrapes DFM for a given company ticker using direct Playwright automation.
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

        # URL Patterns
        base_url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}"
        urls = {
            "profile": f"{base_url}/profile",
            "reports": f"{base_url}/reports",
            "news": f"{base_url}/news-disclosures",
            "corporate_actions": f"{base_url}/corporate-actions",
            "shareholders": f"{base_url}/trading/top-shareholders",
            "trading_data": f"{base_url}/trading/trading-summary",
            "daily_summary": f"{base_url}/trading/daily-summary",
            "foreign_investments": f"{base_url}/trading/foreign-investments"
        }

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
            for _ in range(5):
                show_more = page.locator('button, a').filter(has_text=re.compile(r'Show More|Load More', re.IGNORECASE))
                if await show_more.is_visible():
                    await show_more.click()
                    await page.wait_for_timeout(1000)
                else: break
        except: pass

        # 2. Extract surface links first
        document_links = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'];
            return links
                .filter(a => {
                    const href = (a.href || "").toLowerCase();
                    return docFormats.some(fmt => href.includes(fmt)) || href.includes('download');
                })
                .map(a => ({
                    url: a.href,
                    text: a.textContent.trim(),
                    title: a.title || a.getAttribute('aria-label') || ''
                }));
        }''')

        # 3. Download surface links
        downloaded_count = 0
        found_files = []
        structured_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
        os.makedirs(structured_dir, exist_ok=True)

        for doc in document_links[:limit]:
            try:
                # Deduplication
                text_combined = f"{doc['text']} {doc['title']}"
                if any(ar in text_combined.upper() for ar in ['AR', 'ARABIC', 'عربي']): continue
                
                norm_text = self._normalize_text(text_combined)
                content_key = f"{ticker}_{norm_text}"
                doc_url = doc.get('url', '')
                
                # Check for "Reports" or "Statements" to ensure we don't skip them even if similar name
                is_financial = "REPORT" in norm_text or "STATEMENT" in norm_text or "FINANCIAL" in norm_text

                if not is_financial and (content_key in self.downloaded_texts or (doc_url and doc_url in self.downloaded_urls)): 
                    logger.debug(f"Skipping duplicate surface link: {content_key} or {doc_url}")
                    continue

                # Determine type
                url_lower = doc['url'].lower()
                doc['expected_type'] = 'pdf'
                for fmt in ['xlsx', 'xls', 'docx', 'doc']:
                    if f'.{fmt}' in url_lower: 
                        doc['expected_type'] = fmt; break

                link = page.locator(f'a[href="{doc["url"]}"]').first
                if await link.count() > 0:
                    result = await self.download_manager.download_with_retry(
                        element=link, page=page, doc_info=doc, target_dir=structured_dir
                    )
                    if result:
                        found_files.append(result)
                        downloaded_count += 1
                        self.downloaded_texts.add(content_key)
                        if doc_url: self.downloaded_urls.add(doc_url)
            except: pass

        # 4. Process Nested Dropdowns ("File(s)") row-by-row
        # Use a more specific selector for File(s) buttons to avoid other buttons
        file_buttons = page.locator('button').filter(has_text=re.compile(r'\d+\s*File\(s\)', re.IGNORECASE))
        btn_count = await file_buttons.count()
        if btn_count > 0:
            logger.info(f"Parallel processing {btn_count} nested 'File(s)' dropdowns...")
            
            async def process_dropdown(index):
                try:
                    btn = file_buttons.nth(index)
                    if not await btn.is_visible(): return []
                    await btn.scroll_into_view_if_needed()
                    try: await btn.click(force=True, timeout=3000)
                    except: await btn.evaluate("el => el.click()")
                    await asyncio.sleep(0.5)
                    menu_links = page.locator('div[role="menu"] a, .dropdown-menu a, .dropdown a, .dropdown span').filter(
                        has_text=re.compile(r'Disclosure|Press Rel|Financial|Results|^EP ', re.IGNORECASE)
                    )
                    link_count = await menu_links.count()
                    btn_files = []
                    for j in range(link_count):
                        item = menu_links.nth(j)
                        if await item.is_visible():
                            text = (await item.text_content()).strip()
                            if text.upper() == "FILE(S)" or len(text) < 2: continue
                            norm_text = self._normalize_text(text)
                            content_key = f"{ticker}_{norm_text}"
                            doc_url = (await item.get_attribute('href')) or "javascript:void(0)"
                            
                            is_financial = "REPORT" in norm_text or "STATEMENT" in norm_text or "FINANCIAL" in norm_text

                            if not is_financial and (content_key in self.downloaded_texts or (doc_url != "javascript:void(0)" and doc_url in self.downloaded_urls)):
                                continue
                                
                            doc_info = {"url": doc_url, "text": text, "expected_type": "pdf"}
                            res = await self.download_manager.download_with_retry(element=item, page=page, doc_info=doc_info, target_dir=structured_dir)
                            if res:
                                btn_files.append(res)
                                self.downloaded_texts.add(content_key)
                                if doc_url != "javascript:void(0)": self.downloaded_urls.add(doc_url)
                    return btn_files
                except: return []

            # Sequential processing to prevent race conditions/timeouts with multiple popups
            dropdown_results = []
            for i in range(btn_count):
                res = await process_dropdown(i)
                if res:
                    dropdown_results.append(res)
                    found_files.extend(res)
                    downloaded_count += len(res)
                # Small delay to ensure UI stability between dropdown interactions
                await asyncio.sleep(0.2)

        logger.info(f"  {page_type} download stats: {self.download_manager.get_stats()}")
        return {"documents_downloaded": downloaded_count, "page_type": page_type, "files": found_files}

    def _normalize_text(self, text: str) -> str:
        """Helper to normalize text for consistent key generation and deduplication."""
        if not text: return ""
        # Remove non-alphanumeric and replace with underscores
        norm = re.sub(r'[^\w\s]', '', text.upper())
        # Replace multiple spaces/underscores with single underscore
        norm = re.sub(r'[\s_]+', '_', norm)
        return norm.strip('_')

    async def _expand_file_buttons(self, page: Page, ticker: str = None, page_type: str = None) -> list:
        """Helper to click expand buttons and return revealed links for batch processing"""
        revealed_links = []
        
        # Track view expansion to avoid redundant work
        view_url = page.url
        if view_url in self.expanded_views:
            logger.debug(f"View already expanded: {view_url}")
            return []
        self.expanded_views.add(view_url)

        try:
            # Step 1: Pagination (Show More)
            max_clicks = 10
            clicked = 0
            while clicked < max_clicks:
                buttons = await page.locator('button, a').filter(
                    has_text=re.compile(r'Show More|Load More|View All', re.IGNORECASE)
                ).all()
                
                pag_clicked = False
                for btn in buttons:
                    if await btn.is_visible():
                        try:
                            await btn.scroll_into_view_if_needed()
                            await btn.click(timeout=2000)
                            await page.wait_for_timeout(1000)
                            pag_clicked = True
                            clicked += 1
                        except: pass
                if not pag_clicked: break

            # Step 2: Nested Dropdown expansion
            file_buttons = await page.locator('button').filter(
                has_text=re.compile(r'\d+\s*File\(s\)', re.IGNORECASE)
            ).all()
            
            if file_buttons:
                logger.info(f"Expanding {len(file_buttons)} File(s) dropdowns...")

            for idx, btn in enumerate(file_buttons):
                if not await btn.is_visible():
                    continue
                try:
                    await btn.scroll_into_view_if_needed()
                    await btn.click(timeout=2000)
                    await page.wait_for_timeout(500) 
                    
                    # Collect items revealed under this dropdown
                    items = page.locator('div[role="menu"] a, .dropdown-menu a, .dropdown a, .dropdown span').filter(
                        has_text=re.compile(r'Disclosure|Press Rel|Financial|Results|^EP ', re.IGNORECASE)
                    )
                    
                    count = await items.count()
                    for i in range(count):
                        item = items.nth(i)
                        if await item.is_visible():
                            text = (await item.text_content()).strip()
                            if text.upper() == "FILE(S)" or len(text) < 2:
                                continue
                            
                            revealed_links.append({
                                "url": "javascript:void(0)",
                                "text": text,
                                "title": text,
                                "expected_type": "pdf",
                                "element": item
                            })
                except: pass
            
            return revealed_links
            
        except Exception as e:
            logger.warning(f"Error in _expand_file_buttons: {e}")
            return []

    async def search_ticker(self, query: str) -> tuple:
        return None, None


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
