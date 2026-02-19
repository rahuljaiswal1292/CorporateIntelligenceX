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
from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    TimeoutError as PlaywrightTimeoutError,
)

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

try:
    from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
    from intelligence_hub.utils.storage_manager import StorageManager
    from intelligence_hub.utils.date_extractor import DateExtractor
    from intelligence_hub.scrapers.download_manager import DownloadManager
    from intelligence_hub.scrapers.bot_handler import BotHandler
except ImportError:
    WebScraperConnector = None
    StorageManager = None
    DateExtractor = None
    DownloadManager = None
    BotHandler = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DFMScraper")

# --- Configuration & Storage ---

# Import project-level config
# Import project-level config
from intelligence_hub.config.settings import config

try:
    from intelligence_hub.utils.content_cleaner import clean_html_to_markdown
except ImportError:
    clean_html_to_markdown = lambda x: x  # Fallback if cleaner missing

# --- Scraper ---


class DFMScraper:
    """
    Scraper for Dubai Financial Market (DFM) using direct Playwright automation.
    Handles dynamic content, document downloads, and detailed extraction.
    """

    def __init__(self, connector: WebScraperConnector = None, max_age_years: int = 3):
        # We accept connector to maintain interface compatibility
        self.connector = connector
        self.base_url = "https://www.dfm.ae"
        self.browser: Optional[Browser] = None
        self.playwright = None

        # Initialize enhanced download manager and bot handler
        self.download_manager = DownloadManager(max_age_years=3)
        self.downloaded_texts = set()  # Track downloaded items by text/content
        self.downloaded_urls = (
            set()
        )  # Track downloaded items by URL to avoid duplicates
        self.expanded_views = set()  # Track which views have been expanded
        self.bot_handler = BotHandler() if BotHandler else None

    async def _setup_browser(self):
        """Initialize Playwright browser with stealth settings"""
        logger.info("Initializing Playwright Browser with ENHANCED STEALTH for DFM...")
        self.playwright = await async_playwright().start()

        # Launch with arguments that mimic a real user session
        self.browser = await self.playwright.chromium.launch(
            headless=getattr(config, "HEADLESS", False),
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
        Scrapes DFM for a given company ticker using direct Playwright automation.
        """
        ticker = ticker.upper()
        logger.info(f"Starting Advanced DFM Scrape for {ticker}")

        data = {
            "source": "DFM",
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "news": [],
            "documents": [],
        }

        # Safe initialization
        downloaded_files = []

        # URL Patterns
        base_url = (
            f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}"
        )
        urls = {
            "profile": f"{base_url}/profile",
            "reports": f"{base_url}/reports",
            "news": f"{base_url}/news-disclosures",
            "corporate_actions": f"{base_url}/corporate-actions",
            "shareholders": f"{base_url}/trading/top-shareholders",
            "trading_data": f"{base_url}/trading/trading-summary",
            "daily_summary": f"{base_url}/trading/daily-summary",
            "foreign_investments": f"{base_url}/trading/foreign-investments",
        }

        try:
            # PRE-POPULATE seen downloads from disk
            # This handles resumption and prevents duplicates if files are locked/already present
            for page_type in urls.keys():
                path = os.path.join(
                    config.DATA_DIR, "dfm", ticker, page_type, "structured"
                )
                if os.path.exists(path):
                    for f in os.listdir(path):
                        if f.endswith((".pdf", ".docx", ".doc", ".xlsx", ".xls")):
                            # Use filename as a hint for deduplication
                            base_name = os.path.splitext(f)[0]
                            # Remove counter and use normalized text but maintain years
                            # Heuristic: if suffix is between 1990-2030, assume it's a year, else strip it as counter
                            match = re.search(r"_(\d+)$", base_name)
                            if match:
                                try:
                                    suffix = int(match.group(1))
                                    if (
                                        suffix < 1990 or suffix > 2030
                                    ):  # Only strip if clearly not a year
                                        base_name = base_name[: match.start()]
                                except:
                                    pass

                            norm_name = self._normalize_text(base_name)
                            content_key = f"{ticker}_{norm_name}"
                            self.downloaded_texts.add(content_key)
                            logger.debug(f"Pre-populated existing file: {content_key}")

            await self._setup_browser()

            # Create a context with downloads enabled
            context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            # Limit concurrent page loads to avoid detection/timeouts
            page_semaphore = asyncio.Semaphore(3)

            # Define processing function for each page type
            async def process_page(url, page_type):
                async with page_semaphore:
                    page = await self._create_stealth_page(context)

                logger.info(f"Navigating to {page_type}: {url}")
                try:
                    # Use domcontentloaded for faster initial load
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # Faster settle: wait for specific content instead of fixed time
                    try:
                        await page.wait_for_selector(
                            ".table-flex, .table-flex-vertical, .news-item, .card, .v-window",
                            timeout=10000,
                        )
                    except:
                        logger.debug(
                            f"Timeout waiting for selector on {page_type}, moving on."
                        )

                    # Scroll quickly once to trigger most lazy-loads
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight/2)"
                    )
                    await asyncio.sleep(0.5)
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await asyncio.sleep(0.5)

                    # Store Raw HTML using new page-type structure
                    content = await page.content()
                    StorageManager.save_page_content(
                        content, "dfm", ticker, page_type, "html", "page"
                    )

                    # Convert and Store Clean Markdown
                    try:
                        md_content = clean_html_to_markdown(content)
                        StorageManager.save_page_content(
                            md_content, "dfm", ticker, page_type, "md", "page_clean"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to convert/save markdown for {page_type}: {e}"
                        )

                    # Extract Content and download documents
                    extracted_data = {}

                    if page_type == "profile":
                        extracted_data = await self._extract_profile(
                            page, ticker, page_type
                        )
                    elif page_type == "reports":
                        extracted_data = await self._interact_and_extract_reports(
                            page, ticker, page_type
                        )
                    elif page_type == "daily_summary":
                        extracted_data = await self._extract_daily_summary(
                            page, ticker, page_type
                        )
                    elif page_type == "trading_data":
                        # Trading summary also has Download Excel button
                        extracted_data = await self._extract_trading_data(
                            page, ticker, page_type
                        )
                    elif page_type == "news":
                        extracted_data = await self._extract_news(
                            page, ticker, page_type
                        )
                    elif page_type == "corporate_actions":
                        extracted_data = await self._extract_corporate_actions(
                            page, ticker, page_type
                        )
                    elif page_type == "shareholders":
                        extracted_data = await self._extract_shareholders(
                            page, ticker, page_type
                        )
                    elif page_type == "foreign_investments":
                        extracted_data = await self._extract_foreign_investments(
                            page, ticker, page_type
                        )

                    await page.close()
                    return (page_type, extracted_data)
                except Exception as e:
                    logger.error(f"Error processing {page_type}: {e}")
                    await page.close()
                    return (page_type, None)

            # Execute tasks
            tasks = [
                process_page(urls["profile"], "profile"),
                process_page(urls["reports"], "reports"),
                process_page(urls["news"], "news"),
                process_page(urls["corporate_actions"], "corporate_actions"),
                process_page(urls["shareholders"], "shareholders"),
                process_page(urls["trading_data"], "trading_data"),
                process_page(urls["daily_summary"], "daily_summary"),
                process_page(urls["foreign_investments"], "foreign_investments"),
            ]

            results = await asyncio.gather(*tasks)

            # Merge Results
            for page_type, result in results:
                if result:
                    if page_type == "profile":
                        data["profile"] = result
                    elif page_type == "reports":
                        data["financials"] = result
                    elif page_type == "news":
                        data["news"] = result
                    else:
                        # Add other page types directly to data
                        data[page_type] = result

                    # Collect downloaded files from result
                    if isinstance(result, dict) and "files" in result:
                        downloaded_files.extend(result["files"])

            data["documents"] = list(set(downloaded_files))  # Deduplicate

            # Save final structured data
            StorageManager.save_structured(data, "dfm", ticker)

            return data

        except Exception as e:
            logger.error(f"Fatal error in scrape_company: {e}")
            import traceback

            traceback.print_exc()
            return data
        finally:
            await self._teardown_browser()

    async def _extract_profile(self, page: Page, ticker: str, page_type: str) -> dict:
        """Extract profile information from page content"""
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "listing_date": "NOT AVAILABLE",
            "isin": "NOT AVAILABLE",
        }

        # Company Name
        h1 = soup.find("h1")
        if h1:
            profile["company_name"] = h1.get_text(strip=True)

        # Try finding key-value pairs in profile section
        # Strategy 1: Table Rows
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True).lower()
                val = cols[1].get_text(strip=True)
                self._update_profile_field(profile, key, val)

        # Strategy 2: Description Lists (dl, dt, dd)
        for dt in soup.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd:
                key = dt.get_text(strip=True).lower()
                val = dd.get_text(strip=True)
                self._update_profile_field(profile, key, val)

        # Strategy 3: Divs with specific classes or structure (common in modern frameworks)
        # Look for "label" or "key" classes near values
        # Simplifying: search text nodes if still missing critical info?

        return profile

    def _update_profile_field(self, profile, key, val):
        if "sector" in key:
            profile["sector"] = val
        elif "listing date" in key:
            profile["listing_date"] = val
        elif "isin" in key:
            profile["isin"] = val

    async def _interact_and_extract_reports(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """
        Interact with Reports page to download all English documents for years 2020+.
        Iterates through relevant year tabs and extracts from each.
        """
        logger.info("Interacting with Reports page (2020-2026 focus)...")

        all_downloaded_files = []
        downloaded_count = 0

        # Define target years (Current year back to 2020)
        current_year = datetime.now().year
        # Ensure we cover at least 2020 to current
        # Define target years (Current year back to 2020)
        current_year = datetime.now().year
        # Ensure we cover at least 2020 to current
        target_years = sorted(
            list(set([str(y) for y in range(2020, current_year + 2)])), reverse=True
        )
        logger.info(f"Target years for reports: {target_years}")
        # Parallel Execution: Focused on top 5 years for <30s target
        target_years = sorted(
            list(set([str(y) for y in range(2020, 2027)])), reverse=True
        )
        # We don't limit slice here to ensure we catch all valid years requested
        logger.info(f"Target years for parallel reports: {target_years}")

        sem = asyncio.Semaphore(3)

        async def process_year_tab(year):
            async with sem:
                year_page = await self._create_stealth_page(page.context)
                try:
                    await year_page.goto(page.url, wait_until="commit")
                    tabs = year_page.locator("button, a, span, li").filter(
                        has_text=re.compile(rf"^\s*{year}\s*$", re.IGNORECASE)
                    )
                    if await tabs.count() == 0:
                        tabs = year_page.locator(f"text={year}")
                    if await tabs.count() > 0:
                        logger.info(f"Processing Year Parallel: {year}")
                        await tabs.first.click(force=True)
                        await asyncio.sleep(1)
                        res = await self._generic_document_extract(
                            year_page, ticker, page_type, limit=100
                        )
                        return res.get("files", [])
                    return []
                except:
                    return []
                finally:
                    await year_page.close()

        tasks = [process_year_tab(y) for y in target_years]
        year_results = await asyncio.gather(*tasks)
        for files in year_results:
            if files:
                all_downloaded_files.extend(files)
                downloaded_count += len(files)

        res_current = await self._generic_document_extract(
            page, ticker, page_type, limit=100
        )
        if res_current and "files" in res_current:
            all_downloaded_files.extend(res_current["files"])
            downloaded_count += len(res_current["files"])

        unique_files = list(set(all_downloaded_files))
        logger.info(
            f"Parallel Reports complete: {len(unique_files)} unique files found."
        )
        return {
            "documents_downloaded": downloaded_count,
            "page_type": page_type,
            "files": unique_files,
        }

    async def _extract_daily_summary(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """
        Specific extraction for Daily Summary page which uses a Button instead of a Link.
        """
        logger.info(f"Extracting Daily Summary for {ticker}...")
        download_dir = os.path.join(
            config.DATA_DIR, "dfm", ticker, page_type, "structured"
        )
        os.makedirs(download_dir, exist_ok=True)

        downloaded_count = 0
        found_files = []

        try:
            # Locate the "Download Excel" button
            # It has class "btn btn-download btn-primary" and text "Download Excel"
            button = (
                page.locator("button.btn-download")
                .filter(has_text="Download Excel")
                .first
            )

            if await button.count() > 0:
                logger.info("Found Daily Summary Download Button. Clicking...")

                async with page.expect_download(timeout=15000) as download_info:
                    await button.click()

                download = await download_info.value
                suggested_filename = download.suggested_filename

                # Enforce .xls extension/name if generic
                if "export" in suggested_filename.lower() or not suggested_filename:
                    suggested_filename = f"{ticker}_Daily_Summary.xls"

                filepath = os.path.join(download_dir, suggested_filename)
                await download.save_as(filepath)

                logger.info(f"Downloaded Daily Summary: {filepath}")
                found_files.append(filepath)
                downloaded_count += 1
            else:
                logger.warning("Daily Summary download button not found.")

        except Exception as e:
            logger.error(f"Failed to download Daily Summary: {e}")

        return {
            "documents_downloaded": downloaded_count,
            "page_type": page_type,
            "files": found_files,
        }

    async def _extract_trading_data(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """
        Specific extraction for Trading Summary page (Button + Table).
        """
        logger.info(f"Extracting Trading Data for {ticker}...")
        download_dir = os.path.join(
            config.DATA_DIR, "dfm", ticker, page_type, "structured"
        )
        os.makedirs(download_dir, exist_ok=True)

        downloaded_count = 0
        found_files = []
        trading_summary = {}

        try:
            # 1. Download Excel
            button = (
                page.locator("button.btn-download")
                .filter(has_text="Download Excel")
                .first
            )

            if await button.count() > 0:
                logger.info("Found Trading Data Download Button. Clicking...")
                try:
                    async with page.expect_download(timeout=15000) as download_info:
                        await button.click()

                    download = await download_info.value
                    suggested_filename = download.suggested_filename
                    if "export" in suggested_filename.lower() or not suggested_filename:
                        suggested_filename = f"{ticker}_Trading_Summary.xls"

                    filepath = os.path.join(download_dir, suggested_filename)
                    await download.save_as(filepath)
                    found_files.append(filepath)
                    downloaded_count += 1
                except:
                    pass

            # 2. Extract Table Data (Key metrics)
            # Typically key value pairs in cards or divs
            items = page.locator(".card-body .item, .summary-item, tr")
            count = await items.count()
            for i in range(count):
                text = (await items.nth(i).text_content()).strip()
                # Split by newline or separator
                parts = [p.strip() for p in text.split("\n") if p.strip()]
                if len(parts) >= 2:
                    key = parts[0].lower()
                    val = parts[1]
                    trading_summary[key] = val

        except Exception as e:
            logger.error(f"Failed to process Trading Data: {e}")

        return {
            "documents_downloaded": downloaded_count,
            "page_type": page_type,
            "files": found_files,
            "summary": trading_summary,
        }

    async def _extract_news(self, page: Page, ticker: str, page_type: str) -> dict:
        """Extract news items (Top 4 recent)."""
        logger.info(f"Extracting News for {ticker} (Top 4)...")

        news_items = []
        downloaded_files = []

        try:
            # 1. Expand a bit to ensure we have recent items
            try:
                for _ in range(2):
                    show_more = page.locator("button, a").filter(
                        has_text=re.compile(r"Show More|Load More", re.IGNORECASE)
                    )
                    if await show_more.is_visible():
                        await show_more.scroll_into_view_if_needed()
                        await show_more.click()
                        await page.wait_for_timeout(1000)
                    else:
                        break
            except:
                pass

            # 2. Extract All Items
            items = page.locator(".card, .news-item, .v-card, tr")
            count = await items.count()

            parsed_items = []

            for i in range(count):
                item = items.nth(i)
                if not await item.is_visible():
                    continue

                text = await item.text_content()
                if len(text.strip()) < 10:
                    continue

                news_item = {
                    "raw_text": text.strip(),
                    "date": None,
                    "date_str": "Unknown",
                    "title": "Unknown",
                    "link": None,
                    "element": item,
                }

                # Title
                title_el = item.locator("h3, h4, strong, .title").first
                if await title_el.count() > 0:
                    news_item["title"] = (await title_el.text_content()).strip()
                else:
                    # Fallback to first line of text
                    lines = text.strip().split("\n")
                    if lines:
                        news_item["title"] = lines[0].strip()

                # Link
                link_el = item.locator("a").first
                if await link_el.count() > 0:
                    news_item["link"] = await link_el.get_attribute("href")

                # Date Parsing
                # Try explicit date element?
                date_el = item.locator("time, .date, .timestamp").first
                date_text = ""
                if await date_el.count() > 0:
                    date_text = await date_el.text_content()
                else:
                    # Regex search in full text
                    date_match = re.search(r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})", text)
                    if date_match:
                        date_text = date_match.group(1)

                if date_text:
                    news_item["date_str"] = date_text.strip()
                    try:
                        news_item["date"] = datetime.strptime(
                            news_item["date_str"], "%d %b %Y"
                        )
                    except:
                        try:
                            news_item["date"] = datetime.strptime(
                                news_item["date_str"], "%d %B %Y"
                            )
                        except:
                            pass

                parsed_items.append(news_item)

            # 3. Sort by Date Descending
            # Items without date go to bottom? or top? Assume top if "just now"?
            # DFM usually sorts by date safely. If date parsing fails, keep original order.

            # Filter valid
            valid_items = [i for i in parsed_items if i["date"]]
            invalid_items = [i for i in parsed_items if not i["date"]]

            # Sort valid
            valid_items.sort(key=lambda x: x["date"], reverse=True)

            # Combine (Valid first, then invalid presumed old/unknown)
            sorted_items = valid_items + invalid_items

            # 4. Take Top 4
            top_4 = sorted_items[:4]

            # 5. Process Top 4 (Download + Store)
            structured_dir = os.path.join(
                config.DATA_DIR, "dfm", ticker, page_type, "structured"
            )
            os.makedirs(structured_dir, exist_ok=True)

            for item in top_4:
                # Add to result list
                news_items.append(
                    {
                        "date": item["date_str"],
                        "title": item["title"],
                        "link": item["link"] or "",
                    }
                )

                # Download if link exists
                if item["link"] and item["link"] != "javascript:void(0)":
                    doc_info = {
                        "url": item["link"],
                        "text": item["title"],
                        "expected_type": "pdf",
                    }
                    # Find the link element again to click it?
                    # Prefer using the URL download strategy if possible or finding the element within the item context
                    link_element = item["element"].locator("a").first
                    if await link_element.count() > 0:
                        res = await self.download_manager.download_with_retry(
                            element=link_element,
                            page=page,
                            doc_info=doc_info,
                            target_dir=structured_dir,
                        )
                        if res:
                            downloaded_files.append(res)

        except Exception as e:
            logger.warning(f"Error extracting news text: {e}")

        return {"news_items": news_items, "files": downloaded_files}

    async def _extract_corporate_actions(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """Extract Corporate Actions (text + files)."""
        logger.info(f"Extracting Corporate Actions for {ticker}...")

        # 1. Download files
        doc_result = await self._generic_document_extract(page, ticker, page_type)
        downloaded_files = doc_result.get("files", [])

        # 2. Extract Table Data (Robust)
        actions = []
        try:
            # Locate table rows
            rows = page.locator("table tr")
            count = await rows.count()

            headers = []

            # Try to find header row (first row with th or distinctive visuals)
            if count > 0:
                # Check first row
                first_row_cells = rows.nth(0).locator("th, td")
                cell_count = await first_row_cells.count()
                texts = []
                for k in range(cell_count):
                    texts.append(
                        (await first_row_cells.nth(k).text_content()).strip().lower()
                    )

                if any(
                    k in texts
                    for k in ["date", "type", "amount", "currency", "ex-dividend"]
                ):
                    headers = texts
                    start_idx = 1
                else:
                    # Assume generic headers?
                    headers = [f"col_{k}" for k in range(cell_count)]
                    start_idx = 0

            # Iterate rows
            for i in range(start_idx, count):
                row = rows.nth(i)
                cols = row.locator("td")
                if await cols.count() == 0:
                    continue

                action = {}
                col_count = await cols.count()
                for c in range(col_count):
                    val = (await cols.nth(c).text_content()).strip()
                    if headers and c < len(headers):
                        action[headers[c]] = val
                    else:
                        action[f"col_{c}"] = val

                if action:
                    actions.append(action)

        except Exception as e:
            logger.warning(f"Error extracting corporate actions table: {e}")

        return {"actions": actions, "files": downloaded_files}

    async def _extract_shareholders(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """Extract Shareholders Data."""
        logger.info(f"Extracting Shareholders for {ticker}...")

        # 1. Download files
        doc_result = await self._generic_document_extract(page, ticker, page_type)
        downloaded_files = doc_result.get("files", [])

        # 2. Extract Table
        shareholders = []
        try:
            rows = page.locator("table tr")
            count = await rows.count()
            for i in range(count):  # Check all rows as header might not be standard
                row = rows.nth(i)
                cols = row.locator("td")
                count_cols = await cols.count()
                if count_cols < 2:
                    continue  # likely header or empty

                # Check if it's a header row disguised as td (contains "Name" "Percentage")
                first_text = (await cols.nth(0).text_content()).strip().lower()
                if "name" in first_text or "shareholder" in first_text:
                    continue

                # Robust extraction: Capture all columns
                sh = {}
                # Assuming typical layout: Name, Percentage
                sh["name"] = (await cols.nth(0).text_content()).strip()

                # Try to identify percentage column by content (%)
                for c in range(1, count_cols):
                    text = (await cols.nth(c).text_content()).strip()
                    if "%" in text:
                        sh["percentage"] = text
                    elif (
                        sh.get("category") is None and len(text) > 3
                    ):  # Maybe category?
                        sh["category"] = text
                    else:
                        sh[f"col_{c}"] = text

                shareholders.append(sh)
        except Exception as e:
            logger.warning(f"Error extracting shareholders: {e}")

        return {"shareholders": shareholders, "files": downloaded_files}

    async def _extract_foreign_investments(
        self, page: Page, ticker: str, page_type: str
    ) -> dict:
        """Extract Foreign Investment Data."""
        logger.info(f"Extracting Foreign Investments for {ticker}...")

        # 1. Download files
        doc_result = await self._generic_document_extract(page, ticker, page_type)
        downloaded_files = doc_result.get("files", [])

        # 2. Extract Table (Limit info)
        limits = {}
        try:
            # Often displayed as key-value cards or a small table
            texts = await page.locator(
                ".card, .foreign-investment-limit, table"
            ).all_text_contents()
            full_text = " ".join(texts)
            limits["raw_summary"] = full_text[:500]  # Capture summary
        except:
            pass

        return {"foreign_investment_data": limits, "files": downloaded_files}

    async def _generic_document_extract(
        self, page: Page, ticker: str, page_type: str, limit: int = 50
    ) -> list:
        """
        Generic document extraction logic used by all page types.
        Handles both surface links and nested dropdowns (row-by-row).
        """
        logger.info(f"Starting document extraction for {page_type}...")

        # 1. Expand "Show More" if present
        try:
            for _ in range(5):
                show_more = page.locator("button, a").filter(
                    has_text=re.compile(r"Show More|Load More", re.IGNORECASE)
                )
                if await show_more.is_visible():
                    await show_more.click()
                    await page.wait_for_timeout(1000)
                else:
                    break
        except:
            pass

        # 2. Extract surface links first
        document_links = await page.evaluate(
            """() => {
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
        }"""
        )

        # 3. Download surface links
        downloaded_count = 0
        found_files = []
        structured_dir = os.path.join(
            config.DATA_DIR, "dfm", ticker, page_type, "structured"
        )
        os.makedirs(structured_dir, exist_ok=True)

        for doc in document_links[:limit]:
            try:
                # Deduplication
                text_combined = f"{doc['text']} {doc['title']}"
                if any(ar in text_combined.upper() for ar in ["AR", "ARABIC", "عربي"]):
                    continue

                norm_text = self._normalize_text(text_combined)
                content_key = f"{ticker}_{norm_text}"
                doc_url = doc.get("url", "")

                # Check for "Reports" or "Statements" to ensure we don't skip them even if similar name
                is_financial = (
                    "REPORT" in norm_text
                    or "STATEMENT" in norm_text
                    or "FINANCIAL" in norm_text
                )

                if not is_financial and (
                    content_key in self.downloaded_texts
                    or (doc_url and doc_url in self.downloaded_urls)
                ):
                    logger.debug(
                        f"Skipping duplicate surface link: {content_key} or {doc_url}"
                    )
                    continue

                # Determine type
                url_lower = doc["url"].lower()
                doc["expected_type"] = "pdf"
                for fmt in ["xlsx", "xls", "docx", "doc"]:
                    if f".{fmt}" in url_lower:
                        doc["expected_type"] = fmt
                        break

                link = page.locator(f'a[href="{doc["url"]}"]').first
                if await link.count() > 0:
                    result = await self.download_manager.download_with_retry(
                        element=link, page=page, doc_info=doc, target_dir=structured_dir
                    )
                    if result:
                        found_files.append(result)
                        downloaded_count += 1
                        self.downloaded_texts.add(content_key)
                        if doc_url:
                            self.downloaded_urls.add(doc_url)
            except:
                pass

        # 4. Process Nested Dropdowns ("File(s)") row-by-row
        # Use a more specific selector for File(s) buttons to avoid other buttons
        file_buttons = page.locator("button").filter(
            has_text=re.compile(r"\d+\s*File\(s\)", re.IGNORECASE)
        )
        btn_count = await file_buttons.count()
        if btn_count > 0:
            logger.info(
                f"Parallel processing {btn_count} nested 'File(s)' dropdowns..."
            )

            async def process_dropdown(index):
                try:
                    btn = file_buttons.nth(index)
                    if not await btn.is_visible():
                        return []
                    await btn.scroll_into_view_if_needed()
                    try:
                        await btn.click(force=True, timeout=3000)
                    except:
                        await btn.evaluate("el => el.click()")
                    await asyncio.sleep(0.5)
                    menu_links = page.locator(
                        'div[role="menu"] a, .dropdown-menu a, .dropdown a, .dropdown span'
                    ).filter(
                        has_text=re.compile(
                            r"Disclosure|Press Rel|Financial|Results|^EP ",
                            re.IGNORECASE,
                        )
                    )
                    link_count = await menu_links.count()
                    btn_files = []
                    for j in range(link_count):
                        item = menu_links.nth(j)
                        if await item.is_visible():
                            text = (await item.text_content()).strip()
                            if text.upper() == "FILE(S)" or len(text) < 2:
                                continue
                            norm_text = self._normalize_text(text)
                            content_key = f"{ticker}_{norm_text}"
                            doc_url = (
                                await item.get_attribute("href")
                            ) or "javascript:void(0)"

                            is_financial = (
                                "REPORT" in norm_text
                                or "STATEMENT" in norm_text
                                or "FINANCIAL" in norm_text
                            )

                            if not is_financial and (
                                content_key in self.downloaded_texts
                                or (
                                    doc_url != "javascript:void(0)"
                                    and doc_url in self.downloaded_urls
                                )
                            ):
                                continue

                            doc_info = {
                                "url": doc_url,
                                "text": text,
                                "expected_type": "pdf",
                            }
                            res = await self.download_manager.download_with_retry(
                                element=item,
                                page=page,
                                doc_info=doc_info,
                                target_dir=structured_dir,
                            )
                            if res:
                                btn_files.append(res)
                                self.downloaded_texts.add(content_key)
                                if doc_url != "javascript:void(0)":
                                    self.downloaded_urls.add(doc_url)
                    return btn_files
                except:
                    return []

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

        logger.info(
            f"  {page_type} download stats: {self.download_manager.get_stats()}"
        )
        return {
            "documents_downloaded": downloaded_count,
            "page_type": page_type,
            "files": found_files,
        }

    def _normalize_text(self, text: str) -> str:
        """Helper to normalize text for consistent key generation and deduplication."""
        if not text:
            return ""
        # Remove non-alphanumeric and replace with underscores
        norm = re.sub(r"[^\w\s]", "", text.upper())
        # Replace multiple spaces/underscores with single underscore
        norm = re.sub(r"[\s_]+", "_", norm)
        return norm.strip("_")

    async def _expand_file_buttons(
        self, page: Page, ticker: str = None, page_type: str = None
    ) -> list:
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
                buttons = (
                    await page.locator("button, a")
                    .filter(
                        has_text=re.compile(
                            r"Show More|Load More|View All", re.IGNORECASE
                        )
                    )
                    .all()
                )

                pag_clicked = False
                for btn in buttons:
                    if await btn.is_visible():
                        try:
                            await btn.scroll_into_view_if_needed()
                            await btn.click(timeout=2000)
                            await page.wait_for_timeout(1000)
                            pag_clicked = True
                            clicked += 1
                        except:
                            pass
                if not pag_clicked:
                    break

            # Step 2: Nested Dropdown expansion
            file_buttons = (
                await page.locator("button")
                .filter(has_text=re.compile(r"\d+\s*File\(s\)", re.IGNORECASE))
                .all()
            )

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
                    items = page.locator(
                        'div[role="menu"] a, .dropdown-menu a, .dropdown a, .dropdown span'
                    ).filter(
                        has_text=re.compile(
                            r"Disclosure|Press Rel|Financial|Results|^EP ",
                            re.IGNORECASE,
                        )
                    )

                    count = await items.count()
                    for i in range(count):
                        item = items.nth(i)
                        if await item.is_visible():
                            text = (await item.text_content()).strip()
                            if text.upper() == "FILE(S)" or len(text) < 2:
                                continue

                            revealed_links.append(
                                {
                                    "url": "javascript:void(0)",
                                    "text": text,
                                    "title": text,
                                    "expected_type": "pdf",
                                    "element": item,
                                }
                            )
                except:
                    pass

            return revealed_links

        except Exception as e:
            logger.warning(f"Error in _expand_file_buttons: {e}")
            return []

    async def search_ticker(self, query: str) -> tuple:
        """
        Search for ticker using Web Search (DuckDuckGo) targeting DFM.
        Returns (ticker, company_name)
        """
        try:
            # Lazy import
            from intelligence_hub.utils.web_search import WebSearch
            import urllib.parse

            # Search query specific to DFM
            search_query = f"{query} site:dfm.ae company profile"
            results = WebSearch.search(search_query, max_results=5)

            for res in results:
                url = res.get("href", "").lower()
                title = res.get("title", "")

                # Check for ticker pattern in URL
                # DFM: dfm.ae/the-exchange/market-information/company/TICKER/profile...
                if "/company/" in url:
                    try:
                        parts = url.split("/company/")
                        if len(parts) > 1:
                            ticker_part = parts[1].split("/")[0]
                            ticker = ticker_part.upper().strip()

                            if len(ticker) >= 2 and len(ticker) < 12:
                                # Clean potential garbage
                                if "?" in ticker:
                                    ticker = ticker.split("?")[0]

                                company_name = title.split("|")[0].strip()
                                return ticker, company_name
                    except:
                        pass

            logger.warning(f"DFM search for '{query}' found no tickers.")
            return None, None

        except Exception as e:
            logger.error(f"Error searching DFM ticker: {e}")
            return None, None


if __name__ == "__main__":
    import asyncio

    tickers = [
        "EMAAR",
    ]

    async def main():
        scraper = DFMScraper()

        # Test Search
        print("Testing Search...")
        t, n = await scraper.search_ticker("Emaar properties")
        print(f"Found: {t} - {n}")

        if t:
            await scraper.scrape_company(t)

    asyncio.run(main())
