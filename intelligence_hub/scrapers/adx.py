
import logging
import asyncio
import os
import json
import re
import time
import csv
from typing import Optional, Dict, List, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urljoin

# Third-party imports
from bs4 import BeautifulSoup, NavigableString, Comment
import html2text
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

try:
    from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
    from intelligence_hub.utils.storage_manager import StorageManager
except ImportError:
    WebScraperConnector = None
    StorageManager = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ADXScraper")

# --- Configuration & Storage ---

# Import project-level config
from intelligence_hub.config.settings import config

# StorageManager imported from utils

# --- Advanced Playwright Logic ---

class ADXScraper:
    """
    Advanced Scraper for ADX using direct Playwright automation.
    Handles dynamic content, document downloads, and detailed extration.
    """
    
    def __init__(self, connector: WebScraperConnector = None):
        # We accept connector to maintain interface compatibility, but we primarily use internal Playwright logic
        self.connector = connector
        self.base_url = "https://www.adx.ae"
        self.browser: Optional[Browser] = None
        self.playwright = None
        
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
            "documents": []
        }

        # URL Patterns
        urls = {
            "overview": f"https://www.adx.ae/main-market/company-profile/overview?symbols={ticker}",
            "financials": f"https://www.adx.ae/main-market/company-profile/financial-reports?symbols={ticker}",
            "disclosures": f"https://www.adx.ae/main-market/company-profile/disclosures?symbols={ticker}",
            "fundamentals": f"https://www.adx.ae/main-market/company-profile/fundamentals?symbols={ticker}",
            "shareholders": f"https://www.adx.ae/main-market/company-profile/shareholder-and-board?symbols={ticker}",
        }

        try:
            await self._setup_browser()
            
            # Create a context with downloads enabled
            context = await self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Setup download handler
            download_dir = os.path.join(config.DATA_DIR, "adx", ticker, "downloads")
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
                    # Use domcontentloaded for faster initial load, especially for financial reports
                    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
                    
                    # Wait for page to settle
                    await page.wait_for_timeout(3000)
                    
                    # Scroll to trigger lazy loading
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                    await page.wait_for_timeout(1000)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(3000) # Final settle
                    
                    # Store Raw HTML using new page-type structure
                    content = await page.content()
                    StorageManager.save_page_content(content, "adx", ticker, page_type, "html", "page")

                    # Extract Content and download documents
                    extracted_data = {}
                    
                    if page_type == "overview":
                        extracted_data = await self._extract_overview(page, ticker, page_type)
                    elif page_type == "financials":
                        extracted_data = await self._interact_and_extract_financials(page, ticker, page_type)
                    elif page_type == "disclosures":
                        extracted_data = await self._extract_disclosures(page, ticker, page_type)
                        
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
                # process_page(urls["disclosures"], "disclosures") # Add if needed
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
            
            data["documents"] = downloaded_files
            
            # Save final structured data
            StorageManager.save_structured(data, "adx", ticker)
            
            return data

        except Exception as e:
            logger.error(f"Fatal error in scrape_company: {e}")
            import traceback
            traceback.print_exc()
            return data
        finally:
            await self._teardown_browser()

    async def _extract_overview(self, page: Page, ticker: str, page_type: str) -> dict:
        """Extract overview profile and metrics"""
        # Wait for dynamic content
        try:
             # Wait for something ensuring load, e.g. price or sector
             await page.wait_for_selector(".adx-profile_details-listedHeader-left-details", timeout=10000)
        except:
             pass
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        profile = {
            "company_name": "NOT AVAILABLE",
            "sector": "NOT AVAILABLE",
            "about": "NOT AVAILABLE"
        }
        
        # Parse logic
        # Parse logic
        # Parse logic
        # 1. Try Header structure
        header = soup.select_one(".adx-profile_details-listedHeader-left-details")
        if header:
            # Usually h2 is Ticker/Short Name and h4 is Full Name
            name_candidates = []
            h2 = header.select_one("h2")
            if h2: name_candidates.append(h2.get_text(strip=True))
            h4 = header.select_one("h4")
            if h4: name_candidates.append(h4.get_text(strip=True))
            
            # Prefer longer name as Company Name
            if name_candidates:
                full_name = max(name_candidates, key=len)
                short_name = min(name_candidates, key=len)
                
                profile["company_name"] = full_name
                # If short name is different, maybe it's sector? Unlikely.
                # Sector is usually in a list below.
                
            # Try to find Sector in Meta list
            # Look for "Sector:" label
            # Generic search in header
            for el in header.parent.find_all(string=lambda text: text and "Sector" in text):
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

            # Heuristic Fallback for Sector
            if profile["sector"] == "NOT AVAILABLE":
                name_upper = profile["company_name"].upper()
                if "BANK" in name_upper:
                    profile["sector"] = "Banks"
                elif "INSURANCE" in name_upper:
                    profile["sector"] = "Insurance"
                elif "REAL ESTATE" in name_upper:
                    profile["sector"] = "Real Estate"
                elif "TELECOM" in name_upper:
                    profile["sector"] = "Telecommunications"

        
        # 2. Fallback: Generic H1/Title
        if profile["company_name"] == "NOT AVAILABLE":
            h1 = soup.select_one("h1")
            if h1: profile["company_name"] = h1.get_text(strip=True)
            elif soup.title:
                profile["company_name"] = soup.title.get_text(strip=True).replace("Company Profile Overview", "").strip(" | ADX")

        # 3. Metrics (Placeholder for now, need valid selectors)
        # Look for labelled values if possible
        # e.g. .metric-label, .metric-value

            
        metrics = {}
        # Try to find key metrics
        # (Add specific selectors based on ADX HTML structure)
        
        return {"profile": profile, "metrics": metrics}

    async def _interact_and_extract_financials(self, page: Page, ticker: str, page_type: str) -> dict:
        """
        Interact with financial page to download all English documents.
        Uses Playwright's download event handler for reliable downloads.
        Supports: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
        """
        logger.info("Interacting with Financials page...")
        
        # 1. Click on Report Type buttons to load different sections
        try:
            buttons = await page.locator('button, a[role="tab"]').filter(has_text=re.compile(r'annual|quarterly|interim', re.IGNORECASE)).all()
            for btn in buttons[:5]:
                if await btn.is_visible():
                    try:
                        await btn.click()
                        await page.wait_for_timeout(2000)
                    except: 
                        pass
        except Exception as e:
            logger.warning(f"Error clicking report type buttons: {e}")

        # 2. Find all document links (PDF and Office formats)
        document_links = await page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const docFormats = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'];
            return links
                .filter(a => {
                    const href = a.href.toLowerCase();
                    return docFormats.some(fmt => href.includes(fmt)) || 
                           href.includes('download') || 
                           href.includes('cdn');
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
            if any(ar in text_combined for ar in ['AR', 'ARABIC', 'عربي', '_AR.', '/AR/']):
                logger.info(f"Skipping Arabic document: {doc['text']}")
                continue
            
            # Include English or neutral documents
            english_docs.append(doc)
        
        logger.info(f"Filtered to {len(english_docs)} English documents.")
        
        # 4. Download documents by clicking links or direct request
        downloaded_count = 0
        download_dir = os.path.join(config.DATA_DIR, "adx", ticker, page_type, "pdfs")
        os.makedirs(download_dir, exist_ok=True)
        logger.info(f"Created download directory: {download_dir}")
        
        # Also create structured directory
        structured_dir = os.path.join(config.DATA_DIR, "adx", ticker, page_type, "structured")
        os.makedirs(structured_dir, exist_ok=True)
        logger.info(f"Created structured directory: {structured_dir}")
        
        for i, doc in enumerate(english_docs[:20]):  # Limit to 20 documents
            try:
                url = doc['url']
                
                # Try method 1: Click to trigger download
                try:
                    link_selector = f'a[href="{url}"]'
                    link = page.locator(link_selector).first
                    
                    if await link.count() > 0:
                        # Try to click and wait for download
                        try:
                            async with page.expect_download(timeout=10000) as download_info:
                                await link.click()
                            
                            download = await download_info.value
                            suggested_filename = download.suggested_filename
                            
                            # Determine target directory based on file extension
                            ext = suggested_filename.lower().split('.')[-1] if '.' in suggested_filename else ''
                            structured_formats = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
                            
                            if ext in structured_formats:
                                target_dir = structured_dir
                            else:
                                target_dir = download_dir
                            
                            filepath = os.path.join(target_dir, suggested_filename)
                            await download.save_as(filepath)
                            
                            downloaded_count += 1
                            logger.info(f"Downloaded ({downloaded_count}): {suggested_filename}")
                            await page.wait_for_timeout(500)
                            continue
                            
                        except Exception as click_error:
                            logger.warning(f"Click download failed, trying direct request: {click_error}")
                            # Fall through to method 2
                except Exception as e:
                    logger.warning(f"Link not found, trying direct request: {e}")
                
                # Method 2: Direct request (fallback)
                try:
                    # Generate filename from URL or text
                    filename = url.split('/')[-1].split('?')[0]
                    if not filename or '.' not in filename:
                        # Try to extract from content-disposition or use doc text
                        filename = f"{doc['text'][:30].replace(' ', '_').replace('/', '_')}.pdf"
                    
                    # Use page context to maintain session/cookies
                    response = await page.context.request.get(url)
                    if response.ok:
                        content = await response.body()
                        
                        # Determine file extension and target directory
                        ext = filename.lower().split('.')[-1] if '.' in filename else 'pdf'
                        structured_formats = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
                        
                        if ext in structured_formats:
                            target_dir = structured_dir
                        else:
                            target_dir = download_dir
                        
                        filepath = os.path.join(target_dir, filename)
                        logger.info(f"Writing file to: {filepath} (size: {len(content)} bytes)")
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        logger.info(f"File written successfully: {filepath}")
                        
                        downloaded_count += 1
                        logger.info(f"Downloaded ({downloaded_count}): {filename} via request")
                        await page.wait_for_timeout(300)
                    else:
                        logger.warning(f"Request failed with status {response.status}: {url}")
                        
                except Exception as req_error:
                    logger.error(f"Both download methods failed for {url}: {req_error}")
                    
            except Exception as e:
                logger.error(f"Error downloading {doc.get('url', 'unknown')}: {e}")
                continue
        
        return {"financials": {"documents_downloaded": downloaded_count}}

    async def _extract_disclosures(self, page: Page, ticker: str, page_type: str) -> dict:
        return {}

    async def search_ticker(self, query: str) -> tuple:
        return None, None

# Run Standalone
if __name__ == "__main__":
    async def main():
        scraper = ADXScraper()
        # Test with verified ticker
        await scraper.scrape_company("FAB")

    asyncio.run(main())
