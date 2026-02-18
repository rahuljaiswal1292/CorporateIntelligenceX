
import logging
import asyncio
import os
import json
import re
import time
from typing import Optional, Dict, List
from datetime import datetime
from urllib.parse import urljoin, unquote

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

# Import project-level config
from intelligence_hub.config.settings import config

# Import content cleaner
try:
    from intelligence_hub.utils.content_cleaner import clean_html_to_markdown
except ImportError:
    clean_html_to_markdown = lambda x: x 

# Import Smart Agents (Optional)
try:
    from intelligence_hub.agents.vectorizing_agent import VectorizingAgent
    from intelligence_hub.agents.summarizer_agent import SummarizerAgent
except ImportError as e:
    logger.warning(f"Smart Agents not available: {e}")
    VectorizingAgent = None
    SummarizerAgent = None

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
        
        # Stability: Track active file writes and locks
        self.active_writes = set()
        self.file_lock = asyncio.Lock()

        # Initialize Smart Agents
        self.vector_agent = VectorizingAgent() if VectorizingAgent else None
        self.summarizer_agent = SummarizerAgent(self.vector_agent) if SummarizerAgent and self.vector_agent else None
        
        # Resource management - limit total concurrent browser pages to 10
        self.semaphore = asyncio.Semaphore(10)

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
    
    async def _handle_download_event(self, download_or_page, ticker, page_type, is_page=False):
        """Centralized handler for both direct downloads and PDF popups."""
        if not download_or_page: return
        page_download_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
        os.makedirs(page_download_dir, exist_ok=True)

        try:
            if is_page:
                url = download_or_page.url
                if any(ext in url.lower() for ext in ['.pdf', 'document', 'download', 'feeds.dfm.ae']):
                    try:
                        response = await download_or_page.context.request.get(url, timeout=45000)
                        if response.status == 200:
                            cd = response.headers.get('content-disposition', '')
                            filename = cd.split('filename=')[-1].strip(' ";') if 'filename=' in cd else ""
                            if not filename: filename = url.split('?')[0].split('/')[-1]
                            
                            filename = unquote(filename)
                            filename = re.sub(r'[%\s_\-]+', ' ', filename).strip()
                            if not filename or len(filename) < 5:
                                filename = f"doc_{int(time.time())}.pdf"
                            if not filename.lower().endswith('.pdf'): filename += '.pdf'
                            
                            path = os.path.join(page_download_dir, filename)
                            if path in self.active_writes: return
                            
                            logger.info(f"Capturing binary: {filename}")
                            body = await response.body()
                            self.active_writes.add(path)
                            try:
                                await self._safe_save_file(path, body)
                            finally:
                                self.active_writes.discard(path)
                    except Exception as e:
                        logger.warning(f"Failed to fetch binary for popup {url}: {e}")
                    finally:
                        try: await download_or_page.close()
                        except: pass
            else:
                suggested_filename = unquote(download_or_page.suggested_filename)
                suggested_filename = re.sub(r'[%\s_\-]+', ' ', suggested_filename).strip()
                path = os.path.join(page_download_dir, suggested_filename)
                
                if path in self.active_writes: return
                self.active_writes.add(path)
                try:
                    await download_or_page.save_as(path)
                    logger.info(f"Downloaded: {suggested_filename}")
                finally:
                    self.active_writes.discard(path)
        except Exception as e:
            logger.error(f"Download event handling failed: {e}")

    async def _teardown_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _safe_save_file(self, path: str, body: bytes):
        """Thread-safe and collision-safe file saving."""
        async with self.file_lock:
            # If path already exists, don't overwrite if it's the same or similar
            if os.path.exists(path) and os.path.getsize(path) > 0:
                try:
                    with open(path, 'rb') as rf:
                        existing_body = rf.read()
                        if body == existing_body:
                            return True # Already exists and is same
                except:
                    pass
                
                # If different content, add a suffix
                base, ext = os.path.splitext(path)
                path = f"{base}_{int(time.time() % 1000)}{ext}"

            try:
                with open(path, 'wb') as f:
                    f.write(body)
                return True
            except Exception as e:
                logger.error(f"Failed to safe-save {path}: {e}")
                return False

    async def _prepare_page_content(self, page: Page, page_type: str):
        """Interact with page elements to ensure all content is loaded."""
        try:
            # Short-lived wait for common selectors - non-critical
            try:
                await page.wait_for_selector(".table-flex, .table-flex-vertical, .news-item, .card, .v-window", timeout=5000)
            except: pass
            
            # Universal Scroll to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(0.3)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.3)
        except Exception as e:
             logger.debug(f"Interaction warning for {page_type}: {e}")

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

        try:
            # PRE-POPULATE seen downloads from disk
            # This handles resumption and prevents duplicates if files are locked/already present
            for page_type in urls.keys():
                path = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
                if os.path.exists(path):
                    for f in os.listdir(path):
                        if f.endswith(('.pdf', '.docx', '.doc', '.xlsx', '.xls')):
                            # Use filename as a hint for deduplication
                            base_name = os.path.splitext(f)[0]
                            # Remove counter and use normalized text but maintain years
                            # Heuristic: if suffix is between 1990-2030, assume it's a year, else strip it as counter
                            match = re.search(r'_(\d+)$', base_name)
                            if match:
                                try:
                                    suffix = int(match.group(1))
                                    if suffix < 1990 or suffix > 2030: # Only strip if clearly not a year
                                        base_name = base_name[:match.start()]
                                except: pass
                                
                            norm_name = self._normalize_text(base_name)
                            content_key = f"{ticker}_{norm_name}"
                            self.downloaded_texts.add(content_key)
                            logger.debug(f"Pre-populated existing file: {content_key}")
            
            await self._setup_browser()
            
            # Create a context with downloads enabled
            context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            
            
            # Define processing function for each page type
            async def process_page(url, page_type):
                # 1. Acquire slot and create page
                async with self.semaphore:
                    page = await self._create_stealth_page(context)
                    try:
                        logger.info(f"Page {page_type}: Navigating to {url}...")
                        await page.goto(url, wait_until="commit", timeout=90000)
                    except Exception as e:
                        logger.error(f"Failed to navigate {page_type}: {e}")
                        try: await page.close()
                        except: pass
                        return (page_type, None)

                # 2. Extract (releasing semaphore slot for other tasks)
                try:
                    download_tasks = []
                    def track_task(coro):
                        task = asyncio.create_task(coro)
                        download_tasks.append(task)
                        return task

                    page.on("download", lambda d: track_task(self._handle_download_event(d, ticker, page_type)))
                    page.on("popup", lambda p: track_task(self._handle_download_event(p, ticker, page_type, is_page=True)))
                    
                    # Prepare page content
                    await self._prepare_page_content(page, page_type)
                    
                    # Capture content
                    content = await page.content()
                    StorageManager.save_page_content(content, "dfm", ticker, page_type, "html", "page")
                    
                    try:
                        md_content = clean_html_to_markdown(content)
                        StorageManager.save_page_content(md_content, "dfm", ticker, page_type, "md", "page_clean")
                    except: pass

                    # Domain-Specific Extraction
                    extracted_data = {}
                    if page_type == "profile":
                        extracted_data = await self._extract_profile(page, ticker, page_type)
                    elif page_type == "reports":
                        extracted_data = await self._interact_and_extract_reports(page, ticker, page_type)
                    elif page_type == "daily_summary":
                        extracted_data = await self._extract_daily_summary(page, ticker, page_type)
                    elif page_type == "trading_data":
                        extracted_data = await self._extract_trading_data(page, ticker, page_type)
                    elif page_type == "news":
                        extracted_data = await self._extract_news(page, ticker, page_type)
                    elif page_type == "corporate_actions":
                        extracted_data = await self._extract_corporate_actions(page, ticker, page_type)
                    elif page_type == "shareholders":
                        extracted_data = await self._extract_shareholders(page, ticker, page_type)
                    elif page_type == "foreign_investments":
                        extracted_data = await self._extract_foreign_investments(page, ticker, page_type)

                    # Wait for background downloads
                    if download_tasks:
                        logger.debug(f"Waiting for {len(download_tasks)} downloads for {page_type}...")
                        await asyncio.wait(download_tasks, timeout=120)

                    return (page_type, extracted_data)

                except Exception as e:
                    logger.error(f"Error processing {page_type}: {e}")
                    return (page_type, None)
                finally:
                    try: await page.close()
                    except: pass

            # Define URLs to scrape
            urls = {
                "profile": f"{base_url}/profile",
                "reports": f"{base_url}/reports",
                "news": f"{base_url}/news",
                "corporate_actions": f"{base_url}/corporate-actions",
                "shareholders": f"{base_url}/shareholders",
                "trading_data": f"{base_url}/trading-data",
                "daily_summary": f"{base_url}/daily-summary",
                "foreign_investments": f"{base_url}/foreign-investments"
            }

            # Execute tasks
            tasks = [process_page(urls[pt], pt) for pt in urls]
            try:
                results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=600)
            except asyncio.TimeoutError:
                logger.warning(f"Global timeout reached for {ticker}. Proceeding with partial data.")
                results = []
            except Exception as e:
                logger.error(f"Gather failed for {ticker}: {e}")
                results = []
            
            # Merge Results
            if results:
                for res in results:
                    if not res or not isinstance(res, tuple): continue
                    page_type, result = res
                    if result:
                        if page_type == "profile":
                            data["profile"] = result
                        elif page_type == "reports":
                            data["financials"] = result
                        elif page_type == "news":
                            data["news"] = result
                        else:
                            data[page_type] = result
                        
                        if isinstance(result, dict) and "files" in result:
                            downloaded_files.extend(result["files"])
                        else:
                            data[page_type] = result

                        # Collect downloaded files from result
                        if isinstance(result, dict) and "files" in result:
                            downloaded_files.extend(result["files"])
            
            data["documents"] = list(set(downloaded_files)) # Deduplicate
            
            # Save final structured data
            StorageManager.save_structured(data, "dfm", ticker)
            
            # # Smart Processing (Vectorize & Summarize)
            # logger.info(f"Starting Smart Processing for {ticker}...")
            # try:
            #     if self.vector_agent:
            #         # A. Vectorize (Ingest PDFs/MDs)
            #         data_dir = os.path.join(config.DATA_DIR, "dfm", ticker)
            #         self.vector_agent.ingest_company_data(ticker, data_dir)
            #     else:
            #         logger.warning("VectorizingAgent not initialized. Skipping ingestion.")
                
            #     if self.summarizer_agent:
            #         # B. Summarize (LLM Extraction)
            #         smart_summary = await self.summarizer_agent.summarize_company(ticker)
                    
            #         # Update structured_data with smart insights
            #         if smart_summary:
            #             data.update(smart_summary)
            #             # Re-save with smart data
            #             StorageManager.save_structured(data, "dfm", ticker)
            #     else:
            #         logger.warning("SummarizerAgent not initialized. Skipping summarization.")
                    
            # except Exception as e:
            #     logger.error(f"Smart Processing failed for {ticker}: {e}")

            # logger.info(f"Successfully scraped and processed {ticker}")
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
        soup = BeautifulSoup(content, 'html.parser')
        
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

    def _update_profile_field(self, profile, key, val):
        if "sector" in key: profile["sector"] = val
        elif "listing date" in key: profile["listing_date"] = val
        elif "isin" in key: profile["isin"] = val

    async def _interact_and_extract_reports(self, page: Page, ticker: str, page_type: str) -> dict:
        """
        Interact with Reports page to download all English documents for years 2020+.
        Iterates through relevant year tabs and extracts from each.
        """
        logger.info("Interacting with Reports page (2020-2026 focus)...")
        
        all_downloaded_files = []
        downloaded_count = 0
        
        # Define target years (Current year back to 2020)
        current_year = datetime.now().year
        target_years = sorted(list(set([str(y) for y in range(2020, current_year + 1)])), reverse=True)
        # Limit to top 6 years to keep it within reasonable time limits
        target_years = target_years[:6]
        logger.info(f"Target years for reports: {target_years}")
        
        sem = asyncio.Semaphore(2)
        async def process_year_tab(year):
            async with self.semaphore:
                year_page = await self._create_stealth_page(page.context)
                try:
                    # Setup tracker for this year tab
                    year_tasks = []
                    def track_year_task(coro):
                        t = asyncio.create_task(coro)
                        year_tasks.append(t)
                        return t

                    year_page.on("download", lambda d: track_year_task(self._handle_download_event(d, ticker, page_type)))
                    year_page.on("popup", lambda p: track_year_task(self._handle_download_event(p, ticker, page_type, is_page=True)))
                    
                    await year_page.goto(page.url, wait_until="commit", timeout=90000)
                    tabs = year_page.locator("button, a, span, li").filter(has_text=re.compile(rf"^\s*{year}\s*$", re.IGNORECASE))
                    if await tabs.count() == 0: tabs = year_page.locator(f"text={year}")
                    
                    if await tabs.count() > 0:
                        logger.info(f"Processing Year Parallel: {year}")
                        await tabs.first.click(force=True)
                        await asyncio.sleep(2)
                        res = await self._generic_document_extract(year_page, ticker, page_type, limit=100)
                        
                        if year_tasks:
                            logger.debug(f"Waiting for {len(year_tasks)} downloads for {year}...")
                            await asyncio.wait(year_tasks, timeout=90)
                        
                        return res.get("files", [])
                    return []
                except Exception as e:
                    logger.warning(f"Error in year tab {year}: {e}")
                    return []
                finally:
                    try: await year_page.close()
                    except: pass

        tasks = [process_year_tab(y) for y in target_years]
        try:
            logger.info(f"Triggering parallel extraction for {len(target_years)} years...")
            year_results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=300)
            if year_results:
                for files in year_results:
                    if files:
                        all_downloaded_files.extend(files)
                        downloaded_count += len(files)
        except asyncio.TimeoutError:
            logger.warning(f"Parallel year processing timed out for {ticker}")
        except Exception as e:
            logger.error(f"Error gathering parallel reports: {e}")

        # Final extraction from the main page
        res_current = await self._generic_document_extract(page, ticker, page_type, limit=100)
        if res_current and "files" in res_current:
            all_downloaded_files.extend(res_current["files"])
            downloaded_count += len(res_current["files"])

        unique_files = list(set(all_downloaded_files))
        logger.info(f"Parallel Reports complete: {len(unique_files)} files found.")
        return {"documents_downloaded": downloaded_count, "page_type": page_type, "files": unique_files}

    async def _extract_daily_summary(self, page: Page, ticker: str, page_type: str) -> dict:
        """
        Specific extraction for Daily Summary page which uses a Button instead of a Link.
        """
        logger.info(f"Extracting Daily Summary for {ticker}...")
        download_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
        os.makedirs(download_dir, exist_ok=True)
        
        downloaded_count = 0
        found_files = []
        
        try:
            # Locate the "Download Excel" button
            # It has class "btn btn-download btn-primary" and text "Download Excel"
            button = page.locator("button.btn-download").filter(has_text="Download Excel").first
            
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
            
        return {"documents_downloaded": downloaded_count, "page_type": page_type, "files": found_files}

    async def _extract_trading_data(self, page: Page, ticker: str, page_type: str) -> dict:
        """
        Specific extraction for Trading Summary page (Button + Table).
        """
        logger.info(f"Extracting Trading Data for {ticker}...")
        download_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
        os.makedirs(download_dir, exist_ok=True)
        
        downloaded_count = 0
        found_files = []
        trading_summary = {}

        try:
            # 1. Download Excel
            button = page.locator("button.btn-download").filter(has_text="Download Excel").first
            
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
                except: pass
            
            # 2. Extract Table Data (Key metrics)
            # Typically key value pairs in cards or divs
            items = page.locator(".card-body .item, .summary-item, tr")
            count = await items.count()
            for i in range(count):
                text = (await items.nth(i).text_content()).strip()
                # Split by newline or separator
                parts = [p.strip() for p in text.split('\n') if p.strip()]
                if len(parts) >= 2:
                    key = parts[0].lower()
                    val = parts[1]
                    trading_summary[key] = val
                    
        except Exception as e:
            logger.error(f"Failed to process Trading Data: {e}")
            
        return {"documents_downloaded": downloaded_count, "page_type": page_type, "files": found_files, "summary": trading_summary}


    async def _extract_news(self, page: Page, ticker: str, page_type: str) -> dict:
        """Extract news items (Top 4 recent)."""
        logger.info(f"Extracting News for {ticker} (Top 4)...")
        
        news_items = []
        downloaded_files = []
        
        try:
            # 1. Expand a bit to ensure we have recent items
            try:
                for _ in range(2):
                    show_more = page.locator('button, a').filter(has_text=re.compile(r'Show More|Load More', re.IGNORECASE))
                    if await show_more.is_visible():
                        await show_more.scroll_into_view_if_needed()
                        await show_more.click()
                        await page.wait_for_timeout(1000)
                    else: break
            except: pass

            # 2. Extract All Items
            items = page.locator(".card, .news-item, .v-card, tr")
            count = await items.count()
            
            parsed_items = []
            
            for i in range(count):
                item = items.nth(i)
                if not await item.is_visible(): continue
                
                text = await item.text_content()
                if len(text.strip()) < 10: continue
                
                news_item = {
                    "raw_text": text.strip(),
                    "date": None,
                    "date_str": "Unknown",
                    "title": "Unknown",
                    "link": None,
                    "element": item
                }
                
                # Title
                title_el = item.locator("h3, h4, strong, .title").first
                if await title_el.count() > 0:
                    news_item["title"] = (await title_el.text_content()).strip()
                else: 
                     # Fallback to first line of text
                     lines = text.strip().split('\n')
                     if lines: news_item["title"] = lines[0].strip()

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
                    date_match = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)
                    if date_match:
                        date_text = date_match.group(1)
                
                if date_text:
                    news_item["date_str"] = date_text.strip()
                    try:
                         news_item["date"] = datetime.strptime(news_item["date_str"], "%d %b %Y")
                    except:
                        try:
                            news_item["date"] = datetime.strptime(news_item["date_str"], "%d %B %Y")
                        except: pass
                
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
            structured_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
            os.makedirs(structured_dir, exist_ok=True)
            
            # 5. Process Top 4 (Download attachments from detail pages)
            for item in top_4:
                # Add to result dictionary
                news_items.append({
                    "date": item["date_str"],
                    "title": item["title"],
                    "link": item["link"] or ""
                })
                
                # If the link looks like a detail page, visit it to find attachments
                if item["link"] and "news-details" in item["link"] and item["link"].startswith("http"):
                    async with self.semaphore:
                        logger.info(f"Visiting news detail: {item['title'][:50]}...")
                        detail_page = await self._create_stealth_page(page.context)
                        try:
                            await detail_page.goto(item["link"], wait_until="commit", timeout=30000)
                            res = await self._generic_document_extract(detail_page, ticker, f"news_detail", limit=3)
                            files = res.get("files", [])
                            if files:
                                logger.info(f"Found {len(files)} attachments in news detail: {item['title'][:30]}")
                                downloaded_files.extend(files)
                        except Exception as e:
                            logger.debug(f"Skipping news detail {item['link']}: {e}")
                        finally:
                            try: await detail_page.close()
                            except: pass

            # Also scan the main news list page for any generic files (disclosures often have File(s) button)
            logger.info("Scanning main news page for generic attachments...")
            doc_result = await self._generic_document_extract(page, ticker, page_type, limit=20)
            downloaded_files.extend(doc_result.get("files", []))

        except Exception as e:
            logger.warning(f"Error extracting news: {e}")
            
        return {
            "news_items": news_items,
            "files": downloaded_files
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

    async def _extract_foreign_investments(self, page: Page, ticker: str, page_type: str) -> dict:
        """Extract Foreign Investment Data."""
        logger.info(f"Extracting Foreign Investments for {ticker}...")
        
        # 1. Download files
        doc_result = await self._generic_document_extract(page, ticker, page_type)
        downloaded_files = doc_result.get("files", [])
        
        # 2. Extract Table (Limit info)
        limits = {}
        try:
            # Often displayed as key-value cards or a small table
            texts = await page.locator(".card, .foreign-investment-limit, table").all_text_contents()
            full_text = " ".join(texts)
            limits["raw_summary"] = full_text[:500] # Capture summary
        except: pass
        
        return {
            "foreign_investment_data": limits,
            "files": downloaded_files
        }
        
    async def _generic_document_extract(self, page: Page, ticker: str, page_type: str, limit: int = 100) -> dict:
        """
        Generic document extraction logic used by all page types.
        Handles both surface links and nested dropdowns (row-by-row).
        """
        logger.info(f"Starting document extraction for {page_type} (limit={limit})...")
        
        # 1. Expand "Show More" if present
        try:
            for _ in range(5):
                show_more = page.locator('button, a').filter(has_text=re.compile(r'Show More|Load More', re.IGNORECASE))
                if await show_more.count() > 0 and await show_more.first.is_visible():
                    await show_more.first.click(timeout=5000)
                    await asyncio.sleep(1)
                else: break
        except Exception as e:
            logger.debug(f"Show More expansion skipped: {e}")

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
                    # Simple click approach - let download event handler capture it
                    try:
                        # Extra check: If we already clicked a link with this URL in this session, skip
                        if doc_url and doc_url in self.downloaded_urls:
                            continue

                        logger.info(f"Triggering download: '{doc['text']}' -> {doc['url'][:60]}...")
                        await link.click(timeout=5000)
                        # Reduced sleep for faster triggering
                        await asyncio.sleep(0.3)
                        found_files.append(doc['text'])  # Track by text
                        downloaded_count += 1
                        self.downloaded_texts.add(content_key)
                        if doc_url: self.downloaded_urls.add(doc_url)
                    except Exception as e:
                        logger.debug(f"Failed to click surface link {doc['text']}: {e}")
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
                            
                            # Simple click approach - let download event handler capture it
                            try:
                                await item.click(timeout=3000)
                                await asyncio.sleep(0.5)  # Wait for download to trigger
                                btn_files.append(text)  # Track by text instead of file path
                                self.downloaded_texts.add(content_key)
                                if doc_url != "javascript:void(0)": self.downloaded_urls.add(doc_url)
                                logger.info(f"Clicked download link: {text}")
                            except Exception as e:
                                logger.debug(f"Failed to click {text}: {e}")
                    return btn_files
                except: return []

            # Sequential processing with timeout protection
            for i in range(btn_count):
                try:
                    # Wrapped each dropdown in a wait_for to prevent infinite stalls
                    res = await asyncio.wait_for(process_dropdown(i), timeout=45)
                    if res:
                        found_files.extend(res)
                        downloaded_count += len(res)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout while processing dropdown {i} on {page_type}")
                except Exception as e:
                    logger.debug(f"Dropdown {i} failed: {e}")
                
                await asyncio.sleep(0.1)

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
    tickers = [
        'AIRARABIA',
        'MASQ', 
        'EMAAR', 
        'TALABAT',
        'EMIRATESNBD',
        'DU',
        ] 

    async def run_scraper():
        scraper = DFMScraper()
        try:
            for ticker in tickers:
                logger.info(f"\n{'='*50}\nSTARTING SCRAPE: {ticker}\n{'='*50}")
                await scraper.scrape_company(ticker)
        except KeyboardInterrupt:
            logger.warning("Scraper interrupted by user (Ctrl+C).")
        except Exception as e:
            logger.error(f"Top-level execution error: {e}")
        finally:
            logger.info("Performing final terminal cleanup...")
            try:
                # Ensure teardown happens before loop starts closing
                await scraper._teardown_browser()
            except: pass

    try:
        # Use a more robust entry point to avoid 'Event loop is closed'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_scraper())
        finally:
            loop.close()
    except KeyboardInterrupt:
        pass
