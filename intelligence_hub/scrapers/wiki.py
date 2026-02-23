import logging
import asyncio
from playwright.async_api import async_playwright
from intelligence_hub.utils.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class WikiScraper:
    """
    Scraper for Wikipedia.
    Fetches Company Profile, History, and Subs.
    """

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/wiki"
        self.browser = None
        self.playwright = None

    async def _get_browser(self):
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
        return self.browser

    async def scrape_profile(self, company_name: str) -> dict:
        """
        Scrapes Wikipedia for Company Profile.
        Tries multiple URL variations.
        """
        # Clean name
        clean_name = company_name.replace("PJSC", "").replace("LLC", "").strip()
        variations = [
            clean_name.replace(" ", "_"),
            clean_name.replace(" ", "_") + "_(company)",
            clean_name.replace(" ", "_")
            + "_(insurance)",  # Specific for Sukoon/Insurance cases
        ]

        html = None
        used_url = None

        browser = await self._get_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            for variant in variations:
                url = f"{self.base_url}/{variant}"
                logger.info(f"Wiki: Scraping {url}...")
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    content = await page.content()
                    if (
                        content
                        and "Wikipedia does not have an article with this exact name"
                        not in content
                    ):
                        html = content
                        used_url = url
                        break
                except Exception as e:
                    logger.warning(f"Wiki: Variation {variant} failed: {e}")

            if (
                not html
                or "Wikipedia does not have an article with this exact name" in html
            ):
                logger.warning(f"Wiki: No article found for {company_name}")
                return {}

            # Use clean name as the identifier for saving
            file_id = clean_name.replace(" ", "_")
            StorageManager.save_raw(html, "wiki", file_id)

            data = {
                "source": "Wikipedia",
                "url": used_url,
                "raw_html_snippet": html[:10000],
            }

            StorageManager.save_structured(data, "wiki", file_id)
            return data
        finally:
            await page.close()
            await context.close()
            if self.browser:
                await self.browser.close()
                await self.playwright.stop()
                self.browser = None
                self.playwright = None
