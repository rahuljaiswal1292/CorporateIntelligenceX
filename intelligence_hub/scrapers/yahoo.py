import logging
import asyncio
from playwright.async_api import async_playwright
from intelligence_hub.utils.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class YahooFinanceScraper:
    """
    Scraper for Yahoo Finance.
    Used as fallback for Price/Financials if Exchange sites fail.
    """

    def __init__(self):
        self.base_url = "https://finance.yahoo.com/quote"
        self.browser = None
        self.playwright = None

    async def _get_browser(self):
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
        return self.browser

    async def scrape_ticker(self, ticker: str, exchange_suffix: str = ".AE") -> dict:
        """
        Scrapes Yahoo Finance for a specific ticker (e.g. EMAAR.AE).
        """
        full_ticker = f"{ticker}{exchange_suffix}"
        url = f"{self.base_url}/{full_ticker}"

        logger.info(f"YF: Scraping {full_ticker}...")

        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            html = await page.content()

            if not html:
                return {}

            # Save Raw
            StorageManager.save_raw(html, "yahoo", full_ticker)

            data = {
                "source": "Yahoo Finance",
                "url": url,
                "raw_html_snippet": html[:5000],  # Truncated for meta
            }

            StorageManager.save_structured(data, "yahoo", full_ticker)
            return data
        except Exception as e:
            logger.error(f"YF: Error scraping {full_ticker}: {e}")
            return {}
        finally:
            await page.close()
            await context.close()
            if self.browser:
                await self.browser.close()
                await self.playwright.stop()
                self.browser = None
                self.playwright = None
