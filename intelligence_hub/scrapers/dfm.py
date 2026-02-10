
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
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DFMScraper")

# --- Configuration & Storage ---

# Import project-level config
# Import project-level config
from intelligence_hub.config.settings import config
try:
    from intelligence_hub.utils.content_cleaner import clean_html_to_markdown
except ImportError:
    clean_html_to_markdown = lambda x: x # Fallback if cleaner missing

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
        self.download_manager = DownloadManager(max_age_years=max_age_years) if DownloadManager else None
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
        ticker = ticker.upper()
        logger.info(f"Starting Advanced DFM Scrape for {ticker}")
        
        data = {
            "source": "DFM", 
            "ticker": ticker,
            "scraped_at": datetime.now().isoformat(),
            "profile": {},
            "financials": {},
            "news": [],
            "documents": []
        }

        # URL Patterns
        base_url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}"
        urls = {
            "profile": f"{base_url}/profile",
            "reports": f"{base_url}/reports",
            "news": f"{base_url}/news-disclosures",
            "corporate_actions": f"{base_url}/corporate-actions",
            "shareholders": f"{base_url}/trading/top-shareholders",
            "historical_data": f"{base_url}/trading/historical-data",
            "trading_data": f"{base_url}/trading/trading-summary",
            "daily_summary": f"{base_url}/trading/daily-summary",
            "foreign_investments": f"{base_url}/trading/foreign-investments"
        }

        try:
            await self._setup_browser()
            
            # Create a context with downloads enabled
            context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Setup download handler logic
            download_dir = os.path.join(config.DATA_DIR, "dfm", ticker, "downloads")
            os.makedirs(download_dir, exist_ok=True)
            
            # Track downloads
            downloaded_files = []

            async def handle_download(download):
                try:
                    suggested_filename = download.suggested_filename
                    path = os.path.join(download_dir, suggested_filename)
                    await download.save_as(path)
                    logger.info(f"Downloaded: {path}")
                    downloaded_files.append(path)
                except Exception as e:
                    logger.error(f"Download failed: {e}")

            # Define processing function for each page type
            async def process_page(url, page_type):
                page = await self._create_stealth_page(context)
                page.on("download", handle_download)
                
                logger.info(f"Navigating to {page_type}: {url}")
                try:
                    # Use domcontentloaded for faster initial load
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Wait for page to settle (DFM is SPA-ish)
                    await page.wait_for_timeout(3000)
                    
                    # Scroll to trigger lazy loading
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                    await page.wait_for_timeout(1000)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(3000) # Final settle
                    
                    # Store Raw HTML using new page-type structure
                    content = await page.content()
                    StorageManager.save_page_content(content, "dfm", ticker, page_type, "html", "page")

                    # Convert and Store Clean Markdown
                    try:
                        md_content = clean_html_to_markdown(content)
                        StorageManager.save_page_content(md_content, "dfm", ticker, page_type, "md", "page_clean")
                    except Exception as e:
                        logger.warning(f"Failed to convert/save markdown for {page_type}: {e}")

                    # Extract Content and download documents
                    extracted_data = {}
                    
                    if page_type == "profile":
                        extracted_data = await self._extract_profile(page, ticker, page_type)
                    elif page_type == "reports":
                        extracted_data = await self._interact_and_extract_reports(page, ticker, page_type)
                    elif page_type == "daily_summary":
                        extracted_data = await self._extract_daily_summary(page, ticker, page_type)
                    elif page_type == "trading_data":
                        # Trading summary also has Download Excel button
                        extracted_data = await self._extract_trading_data(page, ticker, page_type)
                    elif page_type in ["news", "corporate_actions", "shareholders", "historical_data", 
                                     "foreign_investments"]:
                        # Extract documents for all page types
                        extracted_data = await self._generic_document_extract(page, ticker, page_type)
    
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
                process_page(urls["historical_data"], "historical_data"),
                process_page(urls["trading_data"], "trading_data"),
                process_page(urls["daily_summary"], "daily_summary"),
                process_page(urls["foreign_investments"], "foreign_investments")
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
            
            data["documents"] = list(set(downloaded_files)) # Deduplicate
            
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
        soup = BeautifulSoup(content, 'html.parser')
        
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "listing_date": "NOT AVAILABLE",
            "isin": "NOT AVAILABLE"
        }
        
        # Company Name
        h1 = soup.find("h1")
        if h1:
            profile["company_name"] = h1.get_text(strip=True)
            
        # Try finding key-value pairs in profile section
        for row in soup.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) >= 2:
                key = cols[0].get_text(strip=True).lower()
                val = cols[1].get_text(strip=True)
                
                if "sector" in key:
                    profile["sector"] = val
                elif "listing date" in key:
                    profile["listing_date"] = val
                elif "isin" in key:
                    profile["isin"] = val
                    
        return profile

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
        # Ensure we cover at least 2020 to current
        target_years = sorted(list(set([str(y) for y in range(2020, current_year + 2)])), reverse=True)
        logger.info(f"Target years for reports: {target_years}")
        
        # 0. Aggressively expand generic content first logic (before tabs, just in case)
        await self._expand_file_buttons(page)
        
        year_tabs_processed = 0
        
        try:
            # 1. Iterate through target years
            for year in target_years:
                # Flexible locator - try multiple patterns
                tabs = page.locator(f'text=/^\\s*{year}\\s*$/i').or_(page.locator(f'text=/{year}\\s*Reports/i'))
                
                tab_count = await tabs.count()
                logger.info(f"Found {tab_count} tab(s) for year {year}")
                
                if tab_count > 0:
                    first_tab = tabs.first
                    if await first_tab.is_visible():
                        logger.info(f"Processing Year Tab: {year}")
                        try:
                            await first_tab.click()
                            # Increased wait time for content to load
                            await page.wait_for_timeout(3000) 
                            await self._expand_file_buttons(page) # Expand inside tab
                            
                            result = await self._generic_document_extract(page, ticker, page_type, limit=100)
                            if result and "files" in result:
                                all_downloaded_files.extend(result["files"])
                                downloaded_count += result.get("documents_downloaded", 0)
                                logger.info(f"Year {year}: Downloaded {result.get('documents_downloaded', 0)} documents")
                            else:
                                logger.warning(f"Year {year}: No documents found")
                                    
                            year_tabs_processed += 1
                        except Exception as e:
                            logger.warning(f"Failed handling tab {year}: {e}")
                    else:
                        logger.debug(f"Year tab {year} not visible")
                else:
                    logger.debug(f"No tab found for year {year}")

        except Exception as e:
            logger.warning(f"Year tab interaction loop failed: {e}")
            
        # 2. Check default view if no tabs processed OR as a safety net
        if year_tabs_processed == 0 or True: # Always run default view too
             logger.info("Running generic extraction on current/default view.")
             await self._expand_file_buttons(page)
             result = await self._generic_document_extract(page, ticker, page_type, limit=100)
             if result and "files" in result:
                all_downloaded_files.extend(result["files"])
                downloaded_count += result.get("documents_downloaded", 0)

        # Deduplicate files list
        unique_files = list(set(all_downloaded_files))
        logger.info(f"Reports extraction complete: {year_tabs_processed} year tabs processed, {downloaded_count} total downloads, {len(unique_files)} unique files")
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
        Specific extraction for Trading Summary page which uses a Button instead of a Link.
        Similar to Daily Summary extraction.
        """
        logger.info(f"Extracting Trading Data for {ticker}...")
        download_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
        os.makedirs(download_dir, exist_ok=True)
        
        downloaded_count = 0
        found_files = []
        
        try:
            # Locate the "Download Excel" button
            button = page.locator("button.btn-download").filter(has_text="Download Excel").first
            
            if await button.count() > 0:
                logger.info("Found Trading Data Download Button. Clicking...")
                
                async with page.expect_download(timeout=15000) as download_info:
                    await button.click()
                
                download = await download_info.value
                suggested_filename = download.suggested_filename
                
                # Enforce .xls extension/name if generic
                if "export" in suggested_filename.lower() or not suggested_filename:
                    suggested_filename = f"{ticker}_Trading_Summary.xls"
                
                filepath = os.path.join(download_dir, suggested_filename)
                await download.save_as(filepath)
                
                logger.info(f"Downloaded Trading Data: {filepath}")
                found_files.append(filepath)
                downloaded_count += 1
            else:
                logger.warning("Trading Data download button not found.")
                
        except Exception as e:
            logger.error(f"Failed to download Trading Data: {e}")
            
        return {"documents_downloaded": downloaded_count, "page_type": page_type, "files": found_files}


    async def _extract_news(self, page: Page, ticker: str, page_type: str) -> list:
        # Just use generic extraction
        return await self._generic_document_extract(page, ticker, page_type, limit=50)
        
    async def _generic_document_extract(self, page: Page, ticker: str, page_type: str, limit: int = 50) -> dict:
        """
        Generic document extraction logic used by all page types.
        Finds links, filters them, and downloads them.
        """
        logger.info(f"Starting generic document extraction for {page_type}...")
        
        # Ensure expanders are clicked
        await self._expand_file_buttons(page)

        # 1. Find all document links
        # Updated to include items with relevant TEXT even if HREF is generic
        document_links = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'];
            const keywords = ['financial', 'statement', 'report', 'results', 'presentation', '2023', '2024', '2025', '2026'];
            
            return links
                .filter(a => {
                    const href = a.href.toLowerCase();
                    const text = (a.textContent || "").toLowerCase();
                    const title = (a.title || "").toLowerCase();
                    
                    // Condition 1: Extension match
                    if (docFormats.some(fmt => href.includes(fmt))) return true;
                    
                    // Condition 2: Keyword download indicators
                    if (href.includes('download') || href.includes('file')) return true;
                    
                    // Condition 3: Text indicators (for JS links)
                    // Must have meaningful text AND (be a JS link OR generic hash)
                    const isGeneric = href.includes('javascript') || href.endsWith('#');
                    const hasKeyword = keywords.some(k => text.includes(k) || title.includes(k));
                    
                    return isGeneric && hasKeyword;
                })
                .map((a, index) => ({
                    url: a.href,
                    text: a.textContent.trim(),
                    title: a.title || a.getAttribute('aria-label') || '',
                    index: index
                }));
        }''')
        
        logger.info(f"Found {len(document_links)} potential document links on {page_type} page.")
        
        # 2. Filter for English documents
        english_docs = []
        for doc in document_links:
            text_combined = f"{doc['text']} {doc['title']}".upper()
            url_lower = doc['url'].lower()
            
            # Exclude Arabic documents
            if any(ar in text_combined for ar in ['AR', 'ARABIC', 'عربي', '_AR.', '/AR/', 'AR-AE']):
                continue
            
            # Check for Arabic unicode range in text
            if any('\u0600' <= char <= '\u06FF' for char in doc['text']):
                continue

            # NEW: Allow JS/Hash links if they look like reports
            is_valid_url = not ("javascript:" in url_lower or "#" == doc['url'].strip())
            is_relevant_text = any(k in text_combined for k in ['FINANCIAL', 'STATEMENT', 'REPORT', 'RESULTS', '202'])
            
            if not is_valid_url and not is_relevant_text:
                continue

            # PAGE-TYPE-SPECIFIC FILTERING
            if page_type == "news":
                # For news page, exclude financial reports that appear in sidebar/related sections
                # Filter out links with financial report keywords
                if any(keyword in text_combined for keyword in ['FINANCIAL RESULTS', 'QUARTERLY REPORT', 'ANNUAL REPORT', 'EARNINGS']):
                    logger.debug(f"Skipping financial report on news page: {doc['text'][:50]}")
                    continue
                
                # Only include links that look like news/disclosures
                if not any(keyword in text_combined for keyword in ['DISCLOSURE', 'NEWS', 'ANNOUNCEMENT', 'PRESS', 'EP ']):
                    logger.debug(f"Skipping non-news item: {doc['text'][:50]}")
                    continue

            english_docs.append(doc)
        
        # Deduplication based on URL
        # For JS links, URL is useless for dedupe (often same). Use Text+Index as key if URL is generic?
        # Let's use URL if unique, else Text.
        unique_docs = {}
        for d in english_docs:
            key = d['url'] 
            if "javascript" in key.lower() or key.strip() == "#":
                key = f"{d['text']}_{d['index']}"
            unique_docs[key] = d
            
        english_docs = list(unique_docs.values())
        
        logger.info(f"Filtered to {len(english_docs)} English documents for {page_type}.")
        
        # 3. Download documents
        downloaded_count = 0
        
        # Directory for all files (PDFs, Excel, DOC, etc.)
        structured_dir = os.path.join(config.DATA_DIR, "dfm", ticker, page_type, "structured")
        os.makedirs(structured_dir, exist_ok=True)
        
        downloaded_files_list = []
        
        # Use DownloadManager if available for parallel downloads
        if self.download_manager:
            logger.info("Using enhanced DownloadManager with parallel downloads")
            
            # Add expected_type to each document for better filename generation
            for doc in english_docs[:limit]:
                url_lower = doc['url'].lower()
                if '.pdf' in url_lower:
                    doc['expected_type'] = 'pdf'
                elif '.xlsx' in url_lower or '.xls' in url_lower:
                    doc['expected_type'] = 'xlsx' if '.xlsx' in url_lower else 'xls'
                elif '.docx' in url_lower or '.doc' in url_lower:
                    doc['expected_type'] = 'docx' if '.docx' in url_lower else 'doc'
                else:
                    doc['expected_type'] = 'pdf'  # default
            
            # Use parallel batch download
            results = await self.download_manager.download_batch_parallel(
                page=page,
                documents=english_docs[:limit],
                target_dir=structured_dir,
                max_concurrent=10,
                max_retries=3
            )
            
            # Collect successful downloads
            downloaded_files_list = [r for r in results if r is not None]
            downloaded_count = len(downloaded_files_list)
            
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
            # Fallback to old method if DownloadManager not available
            logger.warning("DownloadManager not available, using fallback method")
            # Keep old sequential logic as fallback
            for i, doc in enumerate(english_docs[:limit]): 
                try:
                    url = doc['url']
                    text = doc['text']
                    is_js_link = "javascript:" in url.lower() or "#" == url.strip()
                    
                    # --- Method 1: Click Download (Mandatory for JS) ---
                    try:
                        # Specific selector for efficiency
                        if '"' in url and not is_js_link:
                             link = page.locator(f'xpath=//a[@href="{url}"]').first
                        elif is_js_link:
                             # Use text locator for JS links as fallback
                             # escape quotes
                             safe_text = doc['text'].replace('"', '\\"')
                             link = page.locator(f'a:has-text("{safe_text}")').nth(0) 
                             if await link.count() == 0:
                                 pass
                        else:
                             link = page.locator(f'a[href="{url}"]').first
                             
                        if await link.count() > 0:
                             try:
                                 timeout = 15000 if is_js_link else 10000
                                 async with page.expect_download(timeout=timeout) as download_info:
                                     await link.click()
                                 
                                 download = await download_info.value
                                 suggested_filename = download.suggested_filename
                                 
                                 filepath = os.path.join(structured_dir, suggested_filename)
                                 await download.save_as(filepath)
                                 
                                 downloaded_count += 1
                                 logger.info(f"Downloaded ({downloaded_count}): {suggested_filename}")
                                 downloaded_files_list.append(filepath)
                                 await page.wait_for_timeout(500)
                                 continue
                                 
                             except Exception as click_error:
                                 pass
                    except Exception as e:
                        pass

                    # --- Method 2: Direct Request Fallback (Only if NOT JS) ---
                    if not is_js_link:
                        try:
                            filename = url.split('/')[-1].split('?')[0]
                            if not filename or '.' not in filename:
                                safe_text = "".join([c if c.isalnum() else "_" for c in doc['text'][:30]])
                                filename = f"{safe_text}.pdf"
                            
                            response = await page.context.request.get(url)
                            if response.ok:
                                content = await response.body()
                                
                                content_type = response.headers.get('content-type', '').lower()
                                if 'text/html' in content_type:
                                    logger.warning(f"Skipping {url} - Content-Type is HTML, not a file.")
                                    continue

                                filepath = os.path.join(structured_dir, filename)
                                with open(filepath, 'wb') as f:
                                    f.write(content)
                                
                                downloaded_count += 1
                                logger.info(f"Downloaded ({downloaded_count}): {filename} via request")
                                downloaded_files_list.append(filepath)
                                
                                await page.wait_for_timeout(300)
                            else:
                                logger.warning(f"Request failed with status {response.status}: {url}")
        
                        except Exception as req_error:
                            logger.error(f"Both download methods failed for {url}: {req_error}")

                except Exception as outer_e:
                    logger.error(f"Error processing doc {doc.get('url', 'unknown')}: {outer_e}")
                    continue

        # Scan directory to find what we actually have
        found_files = []
        if os.path.exists(structured_dir):
            found_files.extend([os.path.join(structured_dir, f) for f in os.listdir(structured_dir)])
            
        return {"documents_downloaded": downloaded_count, "page_type": page_type, "files": found_files}

    async def _expand_file_buttons(self, page: Page):
        """Helper to click expand buttons recursively"""
        try:
            # wait for likely buttons
            try:
                await page.wait_for_selector('button', state="attached", timeout=2000)
            except:
                pass
            
            # Max clicks to avoid infinite loop
            max_clicks = 20
            clicked = 0
            
            while clicked < max_clicks:
                # Logic: Find all buttons that have text matching "Show More" / "Load More"
                # "File(s)" buttons are usually just toggles, not load more, but we check them too.
                # Prioritize "Load More" type buttons for pagination.
                buttons = await page.locator('button, a').filter(has_text=re.compile(r'Show More|Load More|View All', re.IGNORECASE)).all()
                
                # Also include "File(s)" expandable buttons, but only click if collapsed? 
                # DFM "File(s)" are usually dropdowns. We should click them once.
                # Let's separate "Load More" (pagination) from "File(s)" (dropdown).
                
                # 1. Click Pagination (Wait for load)
                pag_clicked = False
                for btn in buttons:
                     if await btn.is_visible():
                        try:
                            await btn.scroll_into_view_if_needed()
                            await btn.click(timeout=1000)
                            await page.wait_for_timeout(1000) # Wait for content
                            pag_clicked = True
                            clicked += 1
                        except:
                            pass
                
                if not pag_clicked:
                    break
            
            # 2. Click "File(s)" or "Download" dropdowns (One pass is usually enough if pagination is done)
            buttons = await page.locator('button').filter(has_text=re.compile(r'\d+\s*File\(s\)|Download', re.IGNORECASE)).all()
            for btn in buttons:
                if await btn.is_visible():
                    try:
                        await btn.scroll_into_view_if_needed()
                        await btn.click(timeout=1000)
                        await page.wait_for_timeout(200) 
                    except:
                        pass
                        
            # Allow time for DOM updates
        except Exception:
            pass

    async def search_ticker(self, query: str) -> tuple:
        return None, None

if __name__ == "__main__":
    tickers = [
        # 'AIRARABIA', 
        # 'MASQ', 
        'EMAAR', 
        'TALABAT'
        ]
    for ticker in tickers:
        async def main():
            scraper = DFMScraper()
            await scraper.scrape_company(ticker)

        asyncio.run(main())
