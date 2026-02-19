import logging
import asyncio
import os
import json
import logging
from typing import Optional, Dict
from playwright.async_api import Page, Browser, async_playwright
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

try:
    from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
    from intelligence_hub.utils.storage_manager import StorageManager
    from intelligence_hub.utils.adx_download_manager import DownloadManager
    from intelligence_hub.utils.bot_handler import BotHandler
    from intelligence_hub.utils.content_cleaner import clean_html_to_markdown
except ImportError:
    import requests  # Fallback if not installed, though user added it

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ADXScraper")

# --- Configuration & Storage ---

# Import project-level config
from intelligence_hub.config.settings import config

class Config:
    # Use centralized DATA_DIRECTORY
    from intelligence_hub.config.config import DATA_DIRECTORY

    DATA_DIR = DATA_DIRECTORY
    HEADLESS = False


config = Config


try:
    from intelligence_hub.utils.adx_stock_extractor import ADXStockExtractor
except ImportError:
    ADXStockExtractor = None

# StorageManager imported from utils


# StorageManager is imported from utils


# --- Scraper ---


class ADXScraper:
    """
    Advanced Scraper for ADX using direct Playwright automation.
    Handles dynamic content, document downloads, and detailed extration.
    """

    def __init__(self):
        """
        Initialize ADX Scraper.
        Note: Removed dependency on ScrapingBee/Vendor connectors in favor of direct Playwright.
        """
        self.base_url = "https://www.adx.ae"
        self.browser: Optional[Browser] = None
        self.playwright = None

        # Initialize enhanced download manager and bot handler
        max_age_years = 5
        self.download_manager = (
            DownloadManager(max_age_years=max_age_years)
            if "DownloadManager" in globals()
            else None
        )
        self.bot_handler = BotHandler() if "BotHandler" in globals() else None

        # known companies map
        self.known_companies = {
            "FAB": "First Abu Dhabi Bank",
            "FBI": "First Abu Dhabi Bank (Legacy)",  # Example mapping
            "CBD": "Commercial Bank of Dubai",
        }

        # Concurrency control
        self.semaphore = asyncio.Semaphore(6)

    async def _setup_browser(self):
        """Initialize Playwright browser with stealth settings"""
        logger.info("Initializing Playwright Browser with ENHANCED STEALTH...")
        self.playwright = await async_playwright().start()

        # Launch with arguments that mimic a real user session
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Run headless for speed
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-extensions",
                "--disable-gpu",
            ],
        )

    async def _create_stealth_page(self, context):
        """Create a page with stealth injections"""
        page = await context.new_page()

        # Injection 1: Overwrite the `webdriver` property
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        # Injection 2: Mock Chrome/Plugins
        await page.add_init_script(
            """
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """
        )

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
        ticker = ticker.upper()
        # Canonical name check
        canonical_name = self.known_companies.get(ticker, ticker)

        logger.info(f"Starting Advanced ADX Scrape for {ticker} ({canonical_name})")

        data = {
            "source": "ADX",
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "metrics": {},
            "documents": [],
        }

        # URL Patterns
        # URL Patterns
        urls = {
            "overview": f"https://www.adx.ae/main-market/company-profile/overview?symbols={ticker}",
            "financials": f"https://www.adx.ae/main-market/company-profile/financial-reports?symbols={ticker}",
            "disclosures": f"https://www.adx.ae/main-market/company-profile/disclosures?symbols={ticker}",
            "fundamentals": f"https://www.adx.ae/main-market/company-profile/fundamentals?symbols={ticker}",
            "shareholders": f"https://www.adx.ae/main-market/company-profile/shareholder-and-board?symbols={ticker}",
            "orderbook": f"https://www.adx.ae/main-market/company-profile/orderbook?symbols={ticker}",
            "assembly_meetings": f"https://www.adx.ae/main-market/company-profile/assembly-meetings?symbols={ticker}",
        }

        data = {}

        try:
            await self._setup_browser()

            # Create a context with downloads enabled
            context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            # Define processing function for each page type
            async def process_page(url, page_type):
                async with self.semaphore:
                    page = await self._create_stealth_page(context)

                    # Setup page-specific download handler (in 'structured' subfolder)
                    page_download_dir = os.path.join(
                        config.DATA_DIR, "adx", ticker, page_type, "structured"
                    )
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

                    # For orderbook and overview pages, setup chart extractor BEFORE navigation
                    chart_extractor = None
                    if page_type in ["orderbook", "overview"] and ADXStockExtractor:
                        chart_extractor = ADXStockExtractor()
                        chart_extractor.target_url = url
                        chart_extractor.symbol = (
                            chart_extractor._extract_symbol_from_url(url)
                        )
                        chart_extractor.target_symbol = chart_extractor.symbol
                        # Attach network listeners BEFORE navigation
                        page.on("request", chart_extractor._handle_request)
                        page.on("response", chart_extractor._handle_response)
                        logger.info(
                            f"Setup chart extractor listeners for {ticker} on {page_type} BEFORE navigation"
                        )

                    logger.info(f"Navigating to {page_type}: {url}")
                    try:
                        # Use 'load' for more completeness
                        await page.goto(url, wait_until="load", timeout=90000)

                        # Prepare page (scroll, wait)
                        await self._prepare_page_content(page, page_type)

                        # Extract structured data FIRST for pages that need interaction (like financials)
                        extracted_data = {}
                        if page_type == "overview":
                            extracted_data = await self._extract_overview(
                                page, ticker, page_type
                            )
                            # Also attempt chart extraction on overview as a primary source
                            if chart_extractor:
                                chart_res = (
                                    await self._extract_orderbook_chart_with_extractor(
                                        page, ticker, url, chart_extractor
                                    )
                                )
                                if chart_res and chart_res.get("chart_extracted"):
                                    extracted_data["chart_data"] = chart_res
                        elif page_type == "financials":
                            # This method clicks tabs and triggers data loading
                            extracted_data = (
                                await self._interact_and_extract_financials(
                                    page, ticker, page_type
                                )
                            )
                        elif page_type == "orderbook":
                            # Extract chart data using pre-configured extractor
                            extracted_data = (
                                await self._extract_orderbook_chart_with_extractor(
                                    page, ticker, url, chart_extractor
                                )
                            )
                        elif page_type == "shareholders":
                            extracted_data = await self._extract_shareholders(
                                page, ticker, page_type
                            )
                        elif page_type in [
                            "disclosures",
                            "assembly_meetings",
                            "fundamentals",
                        ]:
                            extracted_data = await self._generic_document_extract(
                                page, ticker, page_type
                            )

                        # Capture content AFTER interaction to ensure dynamic data is present
                        content = await page.content()

                        # Save Raw HTML
                        StorageManager.save_page_content(
                            content, "adx", ticker, page_type, "html", "page"
                        )

                        # Convert and Store Clean Markdown (using raw HTML for best results)
                        try:
                            md_content = clean_html_to_markdown(content)
                            StorageManager.save_page_content(
                                md_content, "adx", ticker, page_type, "md", "page_clean"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to convert/save markdown for {page_type}: {e}"
                            )

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
                process_page(urls["assembly_meetings"], "assembly_meetings"),
            ]

            results = await asyncio.gather(*tasks)

            # Merge Results
            downloaded_files = []
            for page_type, result in results:
                if result:
                    if page_type == "overview":
                        data["profile"] = result.get("profile", {})
                        data["metrics"] = result.get("metrics", {})
                    elif page_type == "financials":
                        data["financials"] = result.get("financials", {})
                    elif page_type == "shareholders":
                        data["shareholders"] = result.get("shareholders", [])

                    # Generic merge for everything else (disclosures, orderbook, etc)
                    if page_type not in ["overview"]:
                        data[page_type] = result

                    # Collect any files/documents identified in the result
                    if isinstance(result, dict) and "files" in result:
                        downloaded_files.extend(result["files"])
                    if isinstance(result, dict) and "documents" in result:
                        if isinstance(result["documents"], list):
                            downloaded_files.extend(result["documents"])
                        elif (
                            isinstance(result["documents"], dict)
                            and "files" in result["documents"]
                        ):
                            downloaded_files.extend(result["documents"]["files"])

            data["documents"] = list(set(downloaded_files))

            # Save final structured data to disk
            StorageManager.save_structured(data, "adx", ticker)

            return data

        except Exception as e:
            logger.error(f"Error scraping company {ticker}: {e}")
            import traceback

            traceback.print_exc()
            return {}
        finally:
            await self._teardown_browser()

    async def search_ticker(self, query: str) -> tuple:
        """
        Searches ADX for a company name and returns (ticker, name).
        """
        logger.info(f"Searching ADX for '{query}'...")
        return None, None

    async def _extract_overview(self, page: Page, ticker: str, page_type: str) -> dict:
        """Extract profile information from overview page."""
        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "about": "NOT AVAILABLE",
        }

        # Generic Parsing Logic
        header_details = soup.select_one(
            ".adx-profile_details-listedHeader-left-details"
        )
        if header_details:
            name = header_details.select_one("h2")
            if name:
                profile["company_name"] = name.get_text(strip=True)

            # Prefer longer name as Company Name
            if name_candidates:
                full_name = max(name_candidates, key=len)
                short_name = min(name_candidates, key=len)

        return {"profile": profile}

            # Try to find Sector in Meta list
            # Look for "Sector:" label
            # Generic search in header
            for el in header.parent.find_all(
                string=lambda text: text and "Sector" in text
            ):
                parent = el.parent
                # Check for value in next sibling or within same text
                txt = parent.get_text(strip=True)
                if ":" in txt:
                    parts = txt.split(":")
                    if len(parts) > 1 and "Sector" in parts[0]:
                        profile["sector"] = parts[1].strip()
                else:
                    # Maybe next sibling?
                    sib = parent.find_next_sibling()
                    if sib:
                        profile["sector"] = sib.get_text(strip=True)

    async def _prepare_page_content(self, page: Page, page_type: str):
        """Interact with page elements to ensure all content is loaded before capture."""
        # 1. Universal Scroll to trigger lazy loading
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await page.wait_for_timeout(500)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
        except:
            pass

        # 2. Page Specific Waits
        if page_type == "financials":
            try:
                # Check for bot detection
                if self.bot_handler and await self.bot_handler.detect_bot_challenge(
                    page
                ):
                    await self.bot_handler.handle_bot_detection(page)

                # Wait for the tabs or documents to appear
                logger.info("Waiting for financial data to render...")

                # Dynamic wait for actual data (PDF links or tables with content)
                await page.wait_for_function(
                    """
                    () => {
                        const hasReports = !!document.querySelector('a[href*=".pdf"], a[href*="Download"]');
                        const tables = document.querySelectorAll('table, .adx-table, .table-responsive');
                        let tableHasContent = false;
                        for (const tbl of tables) {
                            if (tbl.innerText.replace(/[\\u200b-\\u200d\\ufeff]/g, '').trim().length > 20) {
                                tableHasContent = true;
                                break;
                            }
                        }
                        return hasReports || tableHasContent;
                    }
                 """,
                    timeout=30000,
                )
                await page.wait_for_timeout(1000)
            except Exception as e:
                logger.warning(f"Wait timeout on financials: {e}")

        elif page_type == "shareholders":
            logger.info("Waiting for shareholders data mapping...")
            try:
                # Wait for any of the common shareholder tables or headings
                await page.wait_for_selector(
                    ".adx-shareholders-board, .shareholders-board_content, h2",
                    timeout=15000,
                )
                await page.wait_for_timeout(1000)
            except:
                pass

        elif page_type == "overview":
            logger.info("Waiting for overview details...")
            try:
                # Wait for share capital or auditor sections if they appear late
                await page.wait_for_selector(
                    ".sharecard-title, .companyoverview-pra, h3", timeout=15000
                )
                await page.wait_for_timeout(1000)
            except:
                pass

        elif page_type == "orderbook":
            logger.info("Waiting for TradingView chart to render...")
            try:
                # Wait for the iframe or the chart container
                await page.wait_for_selector(
                    ".tradingview-widget-container, iframe, #tv_chart_container",
                    timeout=20000,
                )
                await page.wait_for_timeout(2000)  # Reduced from 5000
            except:
                pass

    async def _extract_orderbook_chart_with_extractor(
        self, page: Page, ticker: str, url: str, extractor: "ADXStockExtractor"
    ) -> dict:
        """
        Extract chart data from orderbook page using a pre-configured ADXStockExtractor.
        Uses the helper method extract_from_page directly.
        """
        logger.info(
            f"Extracting orderbook chart data for {ticker} using helper method..."
        )

        if not extractor:
            logger.warning("ADXStockExtractor not available, skipping chart extraction")
            return {
                "chart_extracted": False,
                "reason": "ADXStockExtractor not available",
            }

        try:
            # Use the helper method from the extractor class
            # This handles listeners (if any new ones needed), waits, and extraction logic
            await extractor.extract_from_page(page, url)

            # Check results
            if extractor.processed_df is not None and not extractor.processed_df.empty:
                logger.info(
                    f"Successfully extracted {len(extractor.processed_df)} chart data points for {ticker}"
                )
                return {
                    "chart_extracted": True,
                    "records_count": len(extractor.processed_df),
                    "date_range": {
                        "start": str(extractor.processed_df["Date"].min()),
                        "end": str(extractor.processed_df["Date"].max()),
                    },
                }
            else:
                logger.warning(f"Chart extraction yielded no data for {ticker}")
                return {"chart_extracted": False, "reason": "No data captured"}

        except Exception as e:
            logger.error(f"Error during chart extraction helper call: {e}")
            return {"chart_extracted": False, "reason": str(e)}

    def _clean_generic_adx_content(self, html_content: str) -> str:
        """Remove generic ADX noise with maximum prejudice."""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Broad Removal of known noise containers
            noise_selectors = [
                ".marqueeWrapperTicker",
                ".ticker-value",
                ".uae-current-date",
                ".language-switcher",
                ".accessbility-container",
                ".login-btn",
                ".mw-btn",
                "header",
                "footer",
                ".adx-header",
                ".adx-footer",
                ".search-btn-responsive",
                ".side-bar",
                ".sidebar",
                ".breadcrumb",
                "nav",
                ".navbar",
                ".adx-top-nav",
                ".social-links",
                ".cookie-banner",
                "#top-nav",
                ".sub-footer",
            ]
            for selector in noise_selectors:
                for element in soup.select(selector):
                    element.decompose()

            # 2. Targeted Removal of ticker-specific lists (using find_all for robustness)
            for ul in soup.find_all("ul", attrs={"aria-label": "tickerValue"}):
                ul.decompose()

            # 3. Heuristic: Remove items containing multiple common ADX tickers (noise lists)
            ticker_keywords = [
                "2POINTZERO",
                "ADAVIATION",
                "ADNOCGAS",
                "LULU",
                "FAB",
                "ADCB",
                "ALDAR",
                "IHC",
                "EAND",
                "ADIB",
            ]
            pattern = re.compile("|".join(ticker_keywords))

            for item in soup.find_all(["li", "tr", "div"]):
                # If a small container contains multiple tickers, it's noise
                txt = item.get_text()
                if 2 < len(txt) < 300:
                    matches = pattern.findall(txt)
                    if len(set(matches)) >= 2:  # At least 2 different noise tickers
                        item.decompose()

            return str(soup)
        except Exception as e:
            logger.warning(f"Error cleaning ADX content: {e}")
            return html_content

    async def _interact_and_extract_financials(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """
        Interact with financial page to download all English documents.
        Enhanced with DownloadManager for reliable downloads with retry, validation, and date filtering.
        """
        logger.info(f"Interacting with Financials page for {ticker}...")

        # Check for bot detection
        if self.bot_handler and await self.bot_handler.detect_bot_challenge(page):
            await self.bot_handler.handle_bot_detection(page, severity="medium")

        # 1. Click on Report Type buttons to load different sections
        # We try to prioritize 'Annual' as it usually has the most data
        try:
            # Look for tab buttons
            tab_selectors = [
                'button:has-text("Annual")',
                '.adx-tab_item:has-text("Annual")',
                'button:has-text("Yearly")',
                'a[role="tab"]:has-text("Annual")',
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
                buttons = (
                    await page.locator('button, a[role="tab"]')
                    .filter(
                        has_text=re.compile(
                            r"annual|yearly|quarterly|interim", re.IGNORECASE
                        )
                    )
                    .all()
                )
                for btn in buttons[:1]:  # Just click the first one if not clicked yet
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
        except:
            pass

        # 2. Find all document links (PDF and Office formats)
        document_links = await page.evaluate(
            """() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'];
            return links
                .filter(a => {
                    const href = a.href.toLowerCase();
                    const hasExt = docFormats.some(fmt => href.endsWith(fmt) || href.includes(fmt + '?'));
                    const isDirect = href.includes('download') || href.includes('cdn') || href.includes('apigateway');
                    return hasExt || isDirect;
                })
                .map((a, index) => ({
                    url: a.href,
                    text: a.textContent.trim(),
                    title: a.title || a.getAttribute('aria-label') || '',
                    index: index
                }));
        }"""
        )

        logger.info(f"Found {len(document_links)} potential document links.")

        # 3. Filter for English documents
        english_docs = []
        for doc in document_links:
            text_combined = f"{doc['text']} {doc['title']} {doc['url']}".upper()

            # Exclude Arabic documents
            if any(
                ar in text_combined
                for ar in ["AR", "ARABIC", "عربي", "_AR.", "/AR/", "AR-AE"]
            ):
                logger.info(f"Skipping Arabic document: {doc['text'][:50]}")
                continue

            # Check for Arabic unicode in text
            if any("\u0600" <= char <= "\u06ff" for char in doc["text"]):
                continue

            # Determine expected file type
            url_lower = doc["url"].lower()
            if ".pdf" in url_lower:
                doc["expected_type"] = "pdf"
            elif ".xlsx" in url_lower or ".xls" in url_lower:
                doc["expected_type"] = "xlsx" if ".xlsx" in url_lower else "xls"
            elif ".docx" in url_lower or ".doc" in url_lower:
                doc["expected_type"] = "docx" if ".docx" in url_lower else "doc"
            else:
                doc["expected_type"] = "pdf"  # default

            english_docs.append(doc)

        logger.info(f"Filtered to {len(english_docs)} English documents.")

        # 4. Download documents using enhanced DownloadManager
        downloaded_count = 0
        failed_downloads = []
        skipped_old = []

        # Directory for all files
        target_dir = os.path.join(
            config.DATA_DIR, "adx", ticker, page_type, "structured"
        )
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
                max_retries=3,
            )

            # Count successful downloads
            downloaded_count = sum(1 for r in results if r is not None)
            failed_downloads = [
                doc for doc, result in zip(english_docs[:50], results) if result is None
            ]

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
                "download_stats": (
                    self.download_manager.get_stats() if self.download_manager else {}
                ),
            }
        }

    async def _generic_document_extract(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """
        Generic document extraction for ADX pages (disclosures, assembly meetings, fundamentals).
        Enhanced with DownloadManager for reliable downloads with retry, validation, and date filtering.
        """
        logger.info(f"Starting generic document extraction for {page_type}...")

        # Check for bot detection
        if self.bot_handler and await self.bot_handler.detect_bot_challenge(page):
            await self.bot_handler.handle_bot_detection(page, severity="low")

        # 1. Find all document links
        document_links = await page.evaluate(
            """() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'];
            return links
                .filter(a => {
                    const href = a.href.toLowerCase();
                    const hasExt = docFormats.some(fmt => href.endsWith(fmt) || href.includes(fmt + '?'));
                    const isDirect = href.includes('download') || href.includes('cdn') || href.includes('apigateway');
                    return hasExt || isDirect;
                })
                .map((a, index) => ({
                    url: a.href,
                    text: a.textContent.trim(),
                    title: a.title || a.getAttribute('aria-label') || '',
                    index: index
                }));
        }"""
        )

        logger.info(
            f"Found {len(document_links)} potential document links on {page_type} page."
        )

        # 2. Filter for English documents and determine expected type
        english_docs = []
        for doc in document_links:
            text_combined = f"{doc['text']} {doc['title']} {doc['url']}".upper()

            # Exclude Arabic documents
            if any(
                ar in text_combined
                for ar in ["AR", "ARABIC", "عربي", "_AR.", "/AR/", "AR-AE"]
            ):
                continue

            # Check for Arabic unicode range in text
            if any("\u0600" <= char <= "\u06ff" for char in doc["text"]):
                continue

            # Determine expected file type
            url_lower = doc["url"].lower()
            if ".pdf" in url_lower:
                doc["expected_type"] = "pdf"
            elif ".xlsx" in url_lower:
                doc["expected_type"] = "xlsx"
            elif ".xls" in url_lower:
                doc["expected_type"] = "xls"
            elif ".csv" in url_lower:
                doc["expected_type"] = "csv"
            elif ".docx" in url_lower:
                doc["expected_type"] = "docx"
            elif ".doc" in url_lower:
                doc["expected_type"] = "doc"
            else:
                doc["expected_type"] = "pdf"  # default

            english_docs.append(doc)

        logger.info(f"Filtered to {len(english_docs)} English documents.")

        # 3. Download documents using enhanced DownloadManager
        downloaded_count = 0
        failed_downloads = []

        target_dir = os.path.join(
            config.DATA_DIR, "adx", ticker, page_type, "structured"
        )
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
                max_retries=3,
            )

            # Collect successful downloads
            downloaded_files_list = [r for r in results if r is not None]
            downloaded_count = len(downloaded_files_list)
            failed_downloads = [
                doc for doc, result in zip(english_docs[:50], results) if result is None
            ]

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
            "download_stats": (
                self.download_manager.get_stats() if self.download_manager else {}
            ),
        }

    async def _extract_shareholders(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """Extract shareholder information using table walking."""
        logger.info(f"Extracting shareholders for {ticker}...")
        try:
            # Wait for any table-like element
            await page.wait_for_selector("table, .adx-table", timeout=10000)

            # Simple JS-based table extraction
            shareholders = await page.evaluate(
                """() => {
                const results = [];
                const rows = document.querySelectorAll('tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        const name = cells[0].innerText.trim();
                        const percent = cells[1].innerText.trim();
                        if (percent.includes('%') || parseFloat(percent) > 0) {
                            results.push({ name, percent });
                        }
                    }
                });
                return results;
            }"""
            )

            # Use generic document extraction for any attachments on the shareholder page
            doc_data = await self._generic_document_extract(page, ticker, page_type)

            return {"shareholders": shareholders, "documents": doc_data}
        except Exception as e:
            logger.error(f"Failed to extract shareholders: {e}")
            return {}

    async def search_ticker(self, query: str) -> tuple:
        return None, None


# Run Standalone
if __name__ == "__main__":
    tickers = [
        # "ADNHC",
        # "ADNOCGAS",
        "ALDAR",
        "ALPHADATA",
        # "EAND",
        "FAB",
        "LULU",
    ]

    # Try loading environment variables
    try:
        from dotenv import load_dotenv

    tickers = [
        "LULU",
        "ADNOCGAS",
    ]

    # Try applying nest_asyncio for notebook/IDE support
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        pass

    async def main():
        print(f"--- Running ADX Scraper for: {tickers} ---")

        scraper = ADXScraper()

        for ticker in tickers:
            print(f"\nProcessing {ticker}...")
            try:
                data = await scraper.scrape_company(ticker)
                print(f"Success: {ticker}")
                if data:
                    print(f"Profile: {data.get('profile')}")
                    financials = data.get("financials", {})
                    if financials:
                        print(f"Financials keys: {list(financials.keys())}")
            except Exception as e:
                print(f"Error scraping {ticker}: {e}")

    asyncio.run(main())
