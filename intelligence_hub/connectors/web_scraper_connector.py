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
    Connector for Web Scraping APIs (ScraperAPI, Scrape.do, ScrapingBee).
    Abstracts vendor specifics behind a common interface.
    Supports PDF and Excel file downloads.
    """
    def __init__(self, api_key: str = None, provider: str = "scraperapi"):
        """
        Initialize the connector.
        
        Args:
            api_key: API key for the scraping service
            provider: Which provider to use ('scraperapi', 'scrape.do', 'scrapingbee')
        """
        self.api_key = api_key or os.getenv("SCRAPER_API_KEY")
        self.provider = provider.lower()
        
        # Configure base URL based on provider
        if self.provider == "scraperapi":
            self.base_url = "https://api.scraperapi.com"
        elif self.provider == "scrape.do":
            self.base_url = "http://api.scrape.do"
        elif self.provider == "scrapingbee":
            self.base_url = "https://app.scrapingbee.com/api/v1"
        else:
            logger.warning(f"Unknown provider '{provider}', defaulting to ScraperAPI")
            self.base_url = "https://api.scraperapi.com"
            self.provider = "scraperapi"
        
        if self.api_key:
            self.mode = "LIVE"
            logger.info(f"Initialized with {self.provider.upper()} in LIVE mode")
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
            params = self._build_params(url, render_js, wait_for)
            
            response = requests.get(self.base_url, params=params, timeout=120)
            
            if response.status_code == 200:
                return response.content.decode("utf-8")
            
            logger.error(f"Web Scraper Error {response.status_code}: {response.text[:500]}")
            
            # Fallback
            if response.status_code in [404, 401, 403, 429, 500]:
                logger.info(f"API Error {response.status_code}. Switching to Playwright Fallback...")
                self.mode = "LOCAL_PLAYWRIGHT"
                if not self.pw_connector and PlaywrightConnector:
                     self.pw_connector = PlaywrightConnector()
                return self._scrape_playwright_sync(url, wait_for, js_scenario)
                
            return ""
        except Exception as e:
            logger.error(f"Web Scraper Exception: {str(e)}")
            logger.info("Exception occurred, trying Playwright Fallback...")
            return self._scrape_playwright_sync(url, wait_for, js_scenario)

    def _build_params(self, url: str, render_js: bool, wait_for: str) -> dict:
        """Build API parameters based on provider."""
        
        if self.provider == "scraperapi":
            # ScraperAPI format: https://api.scraperapi.com?api_key=KEY&url=URL&render=true
            params = {
                "api_key": self.api_key,
                "url": url,
            }
            if render_js:
                params["render"] = "true"
            if wait_for:
                params["wait_for_selector"] = wait_for
            return params
            
        elif self.provider == "scrape.do":
            # Scrape.do format (COMMENTED OUT - LEGACY)
            # params = {
            #     "token": self.api_key,
            #     "url": url,
            #     "super": "true"
            # }
            # if render_js:
            #     params["render"] = "true"
            # if wait_for:
            #     params["waitForSelector"] = wait_for
            # return params
            pass
            
        elif self.provider == "scrapingbee":
            # ScrapingBee format (COMMENTED OUT - ALTERNATIVE)
            # params = {
            #     "api_key": self.api_key,
            #     "url": url,
            #     "render_js": "true" if render_js else "false"
            # }
            # if wait_for:
            #     params["wait_for"] = wait_for
            # return params
            pass
        
        # Default to ScraperAPI
        return {
            "api_key": self.api_key,
            "url": url,
            "render": "true" if render_js else "false"
        }

    def _scrape_playwright_sync(self, url: str, wait_for: str, js_scenario: dict) -> str:
        """Synchronous wrapper for Playwright scraping."""
        if not PlaywrightConnector:
             logger.error("Playwright Connector class not available.")
             return self._scrape_direct(url)
             
        try:
             import asyncio
             # Create new loop for this thread
             new_loop = asyncio.new_event_loop()
             asyncio.set_event_loop(new_loop)
             
             async def runner():
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
            response = self.session.get(url, timeout=30)
                
            if response.status_code == 200:
                 return response.text
            logger.error(f"Direct Scraping Failed {response.status_code}: {response.text[:500]}")
            return ""
        except Exception as e:
             logger.error(f"Direct Scraping Exception: {e}")
             return ""

    async def download_file_async(self, url: str, expected_type: str = None) -> tuple:
        """
        Asynchronously downloads a file (PDF/Excel/Doc).
        
        Args:
            url: URL of the file to download
            expected_type: Expected content type ('pdf', 'excel', 'doc', etc.)
            
        Returns:
            tuple: (file_content: bytes, content_type: str, is_valid: bool)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.download_file, url, expected_type)

    def download_file(self, url: str, expected_type: str = None) -> tuple:
        """
        Downloads a file (binary) with content-type validation.
        
        Args:
            url: URL of the file to download
            expected_type: Expected content type ('pdf', 'excel', 'doc', etc.)
            
        Returns:
            tuple: (file_content: bytes, content_type: str, is_valid: bool)
        """
        logger.info(f"[{self.mode}] Downloading File: {url}")
        
        if self.mode == "MOCK":
             # Return a minimally VALID PDF binary
             return (b"%PDF-1.4\n%Mock PDF", "application/pdf", True)

        try:
            # Try via Web Scraper API first
            if self.mode == "LIVE" and self.api_key:
                params = self._build_download_params(url)
                r = requests.get(self.base_url, params=params, timeout=60)
                
                if r.status_code == 200:
                    content_type = r.headers.get('content-type', '').lower()
                    is_valid = self._validate_content_type(content_type, expected_type)
                    
                    if not is_valid:
                        logger.warning(f"Content-Type mismatch: got '{content_type}', expected '{expected_type}'")
                    
                    return (r.content, content_type, is_valid)
                
                logger.warning(f"Web Scraper download failed {r.status_code}, attempting direct fallback...")
            
            # Fallback: Direct download
            r_direct = self.session.get(url, timeout=60, stream=True)
            if r_direct.status_code == 200:
                content_type = r_direct.headers.get('content-type', '').lower()
                is_valid = self._validate_content_type(content_type, expected_type)
                
                if not is_valid:
                    logger.warning(f"Content-Type mismatch: got '{content_type}', expected '{expected_type}'")
                
                return (r_direct.content, content_type, is_valid)
            
            return (None, None, False)
        except Exception as e:
            logger.error(f"Download Exception: {str(e)}")
            return (None, None, False)

    def _build_download_params(self, url: str) -> dict:
        """Build download parameters based on provider."""
        if self.provider == "scraperapi":
            return {
                "api_key": self.api_key,
                "url": url,
                "render": "false"  # Don't render for file downloads
            }
        elif self.provider == "scrape.do":
            # return {
            #     "token": self.api_key,
            #     "url": url,
            #     "render": "false"
            # }
            pass
        elif self.provider == "scrapingbee":
            # return {
            #     "api_key": self.api_key,
            #     "url": url,
            #     "render_js": "false"
            # }
            pass
        
        # Default
        return {
            "api_key": self.api_key,
            "url": url,
            "render": "false"
        }

    def _validate_content_type(self, content_type: str, expected_type: str = None) -> bool:
        """
        Validate that the content type matches expectations.
        
        Args:
            content_type: Actual content-type from response
            expected_type: Expected type ('pdf', 'excel', 'doc', etc.)
            
        Returns:
            bool: True if valid, False if HTML or mismatch
        """
        if not content_type:
            return True  # Unknown, assume valid
        
        # Reject HTML
        if 'text/html' in content_type:
            return False
        
        # If no expectation, accept any non-HTML
        if not expected_type:
            return True
        
        # Validate expected types
        type_mappings = {
            'pdf': ['application/pdf'],
            'excel': ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
            'doc': ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'csv': ['text/csv'],
            'zip': ['application/zip']
        }
        
        expected_types = type_mappings.get(expected_type.lower(), [])
        return any(et in content_type for et in expected_types)

    def _scrape_mock(self, url: str) -> str:
        """Returns detailed Mock HTML."""
        if "adx.ae" in url:
            return "<html><body><h1>Mock ADX</h1></body></html>"
        elif "dfm.ae" in url:
            return "<html><body><h1>Mock DFM</h1></body></html>"
        return "<html><body>Mock Content</body></html>"
