import logging
import asyncio
import os
import urllib.parse
try:
    from curl_cffi import requests
except ImportError:
    import requests # Fallback
try:
    from intelligence_hub.connectors.playwright_connector import PlaywrightConnector
except ImportError:
    PlaywrightConnector = None

# Configure logging
logger = logging.getLogger("WebScraperConnector")

class WebScraperConnector:
    """
    Connector for a generic Web Scraping API (e.g. Scrape.do, ScrapingBee).
    Abstracts the vendor specifics behind a common interface.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SCRAPER_API_KEY")
        self.base_url = "http://api.scrape.do"
        
        if self.api_key:
            self.mode = "LIVE"
        else:
            self.mode = "LOCAL_PLAYWRIGHT" # Default to local if no key
            if PlaywrightConnector:
                 self.pw_connector = PlaywrightConnector()
                 logger.warning("SCRAPER_API_KEY not found. Running in LOCAL PLAYWRIGHT MODE.")
            else:
                 self.mode = "MOCK"
                 logger.warning("SCRAPER_API_KEY not found and Playwright missing. Running in MOCK MODE.")

        # Session for direct fallback or advanced usage
        if hasattr(requests, "Session"):
             try:
                 self.session = requests.Session(impersonate="chrome")
             except TypeError:
                 self.session = requests.Session()
                 self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        else:
             import requests as std_requests
             self.session = std_requests.Session()
        
        self.pw_connector = None
        if PlaywrightConnector and not hasattr(self, 'pw_connector'):
             self.pw_connector = PlaywrightConnector()

    async def scrape_async(self, url: str, render_js: bool = True, wait_for: str = None, js_scenario: dict = None) -> str:
        """
        Asynchronously scrapes a URL using run_in_executor.
        """
        try:
           loop = asyncio.get_running_loop()
        except RuntimeError:
           loop = asyncio.new_event_loop()
           asyncio.set_event_loop(loop)
           
        return await loop.run_in_executor(None, self.scrape, url, render_js, wait_for, js_scenario)

    def scrape(self, url: str, render_js: bool = True, wait_for: str = None, js_scenario: dict = None) -> str:
        """
        Scrapes a URL.
        """
        logger.info(f"[{self.mode}] Scraping URL: {url} (Render: {render_js})")
        
        if self.mode == "LIVE":
            return self._scrape_live(url, render_js, wait_for, js_scenario)
        elif self.mode == "LOCAL_PLAYWRIGHT":
            return self._scrape_playwright_sync(url, wait_for, js_scenario)
        else:
            return self._scrape_mock(url)

    def _scrape_live(self, url: str, render_js: bool, wait_for: str, js_scenario: dict) -> str:
        """Executes actual API call to the Web Scraper Service."""
        try:
            # Construct Scraper URL
            # API: https://api.scraperapi.com?token=API_KEY&url=URL&render=true
            
            params = {
                "token": self.api_key,
                "url": url,
                "super": "true"
            }
            
            if render_js:
                params["render"] = "true"
            
            if wait_for:
                 params["waitForSelector"] = wait_for 
                 
            # Some providers don't support complex 'js_scenario' directly in URL.
            # We rely on basic render and wait_for selectors.
            
            response = requests.get(self.base_url, params=params, timeout=120) # Extneded timeout for rendering
            
            if response.status_code == 200:
                return response.content.decode("utf-8")
            
            logger.error(f"Web Scraper Error {response.status_code}: {response.text[:500]}")
            
            # Fallback
            if response.status_code in [404, 401, 403, 429, 500]:
                logger.info(f"API Error {response.status_code}. Switching to Playwright Fallback...")
                self.mode = "LOCAL_PLAYWRIGHT" # Switch mode for future calls
                if not self.pw_connector and PlaywrightConnector:
                     self.pw_connector = PlaywrightConnector()
                return self._scrape_playwright_sync(url, wait_for, js_scenario)
                
            return ""
        except Exception as e:
            logger.error(f"Web Scraper Exception: {str(e)}")
            logger.info("Exception occurred, trying Playwright Fallback...")
            return self._scrape_playwright_sync(url, wait_for, js_scenario)

    def _scrape_playwright_sync(self, url: str, wait_for: str, js_scenario: dict) -> str:
        """Synchronous wrapper for Playwright scraping. Creates a fresh instance to avoid loop interactions."""
        if not PlaywrightConnector:
             logger.error("Playwright Connector class not available.")
             return self._scrape_direct(url)
             
        try:
             import asyncio
             # Check if we have a loop
             try:
                 loop = asyncio.get_event_loop()
             except RuntimeError:
                 loop = asyncio.new_event_loop()
                 asyncio.set_event_loop(loop)
                 
             if loop.is_running():
                 # Should not happen in run_in_executor usually, but if so:
                 logger.warning("Event loop is running in sync wrapper. This is unexpected.")
                 pass
             
             # Create new loop for this thread
             new_loop = asyncio.new_event_loop()
             asyncio.set_event_loop(new_loop)
             
             async def runner():
                 # Create FRESH connector for this thread/loop
                 connector = PlaywrightConnector()
                 try:
                     content, page = await connector.scrape(url, wait_for_selector=wait_for, js_scenario=js_scenario)
                     return content
                 finally:
                     await connector.close()
                 
             content = new_loop.run_until_complete(runner())
             new_loop.close()
             
             return content if content else ""
        except Exception as e:
             logger.error(f"Playwright Sync Error: {e}")
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
            logger.error(f"Direct Scraping Failed {response.status_code}: {response.text[:500]}")
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
        Downloads a file (binary).
        """
        logger.info(f"[{self.mode}] Downloading File: {url}")
        
        if self.mode == "MOCK":
             # Return a minimally VALID PDF binary
             return b"%PDF-1.4\n%Mock PDF"

        try:
            # Try via Web Scraper (without render) to avoid blocks
            params = {
                "token": self.api_key,
                "url": url,
                "render": "false"
            }
            
            r = requests.get(self.base_url, params=params, timeout=60)
            
            if r.status_code == 200:
                return r.content
            
            logger.warning(f"Web Scraper download failed {r.status_code}, attempting direct fallback...")
            
            # Fallback Direct
            r_direct = self.session.get(url, timeout=60, stream=True)
            if r_direct.status_code == 200:
                return r_direct.content
            
            return None
        except Exception as e:
            logger.error(f"Download Exception: {str(e)}")
            return None

    def _scrape_mock(self, url: str) -> str:
        """Returns detailed Mock HTML."""
        if "adx.ae" in url:
            return "<html><body><h1>Mock ADX</h1></body></html>"
        elif "dfm.ae" in url:
            return "<html><body><h1>Mock DFM</h1></body></html>"
        return "<html><body>Mock Content</body></html>"
