import logging
import asyncio
from playwright.async_api import async_playwright
import os

logger = logging.getLogger(__name__)

class PlaywrightConnector:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    async def initialize(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False, # Cloudflare bypass
                channel="chrome", # Use real Chrome
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--start-maximized"
                ]
            )
            # Create a persistent context or reuse one
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                accept_downloads=True
            )

    async def scrape(self, url, wait_for_selector=None, js_scenario=None, timeout=60000):
        if not self.context:
            await self.initialize()
            
        page = await self.context.new_page()
        try:
            logger.info(f"Navigating to {url}")
            await page.goto(url, timeout=timeout, wait_until="networkidle")
            
            if js_scenario and "instructions" in js_scenario:
                logger.info("Executing JS Scenario...")
                for instruction in js_scenario["instructions"]:
                    try:
                        if "wait" in instruction:
                            await page.wait_for_timeout(instruction["wait"])
                        elif "click" in instruction:
                            await page.click(instruction["click"])
                        elif "evaluate" in instruction:
                            await page.evaluate(instruction["evaluate"])
                        elif "scroll_y" in instruction:
                            await page.evaluate(f"window.scrollBy(0, {instruction['scroll_y']})")
                        elif "wait_for" in instruction:
                             await page.wait_for_selector(instruction["wait_for"], timeout=10000)
                    except Exception as e:
                        logger.warning(f"Instruction failed {instruction}: {e}")

            if wait_for_selector:
                logger.info(f"Waiting for selector {wait_for_selector}")
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=20000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for selector {wait_for_selector}: {e}")

            content = await page.content()
            return content, page
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            await page.close()
            return None, None
            
    async def get_document_links(self, url):
        """Specific method to extract document links from ADX pages"""
        content, page = await self.scrape(url, wait_for_selector="a[href*='/content/download/']")
        if not page:
            return []
            
        try:
            links = []
            elements = await page.locator("a[href*='/content/download/']").all()
            for el in elements:
                href = await el.get_attribute("href")
                text = await el.text_content()
                if href:
                    links.append({"href": href, "text": text.strip()})
            return links
        finally:
            await page.close()

    async def download_file(self, url, retries=3):
        """Download file using browser context to bypass WAF"""
        if not self.context:
            await self.initialize()

        page = await self.context.new_page()
        try:
            logger.info(f"Downloading {url}...")
            # ADX download links trigger a download attachment
            # We need to expect the download event
            async with page.expect_download(timeout=60000) as download_info:
                # Trigger the download by navigating to the URL or clicking?
                # For ADX, navigating to the link seems to trigger download based on API logs
                # But if it's an API, usually browser handles it.
                # However, page.goto might fail if it's a download.
                # Safer: create a hidden anchor and click it? Or just try goto.
                
                try:
                    await page.goto(url, timeout=60000)
                except Exception as e:
                    # Navigation to a download often throws "net::ERR_ABORTED" or similar.
                    # This is expected if download starts.
                    pass

            download = await download_info.value
            # Save to temporary path or return bytes? 
            # We want bytes to match previous interface
            path = await download.path()
            with open(path, "rb") as f:
                content = f.read()
            return content
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
        finally:
            await page.close()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
