import asyncio
import os
import logging
import re
from typing import Optional, List
from playwright.async_api import async_playwright, Page, Browser

try:
    from intelligence_hub.config.settings import config

    DATA_DIR = config.DATA_DIR
except ImportError:
    DATA_DIR = "data"

try:
    from intelligence_hub.utils.dfm_download_manager import DFMDownloadManager
except ImportError:
    # Fallback if running standalone without package context
    import sys

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from intelligence_hub.utils.dfm_download_manager import DFMDownloadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DFMStockExtractor")


class OverwritingDFMDownloadManager(DFMDownloadManager):
    """
    Subclass that overwrites existing files instead of creating indexed copies.
    """

    def _get_unique_filepath(self, filepath: str) -> str:
        # Simply return the path as-is, causing overwrite
        return filepath


class DFMStockExtractor:
    """
    Standalone extractor for DFM Daily Summary stock data.
    Navigates to the trading/daily-summary page and downloads the Excel file.
    """

    def __init__(self):
        self.download_manager = OverwritingDFMDownloadManager()
        self.browser: Optional[Browser] = None

    async def extract(self, ticker: str):
        """
        Main extraction flow for a single ticker.
        """
        ticker = ticker.upper()
        url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}/trading/daily-summary"

        logger.info(f"Starting extraction for {ticker} at {url}")

        # Define download directory
        # User requested: dfm/<ticker>/daily_summary/structured/
        if DATA_DIR:
            target_dir = os.path.join(
                DATA_DIR, "dfm", ticker, "daily_summary", "structured"
            )
        else:
            target_dir = os.path.join(
                "data", "dfm", ticker, "daily_summary", "structured"
            )

        os.makedirs(target_dir, exist_ok=True)

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,  # Background execution
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1920,1080",
                    "--disable-infobars",
                    "--no-sandbox",
                ],
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                accept_downloads=True,
            )

            # Stealth injections
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            try:
                logger.info(f"Navigating to {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Check for "Loading..."
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass

                # Wait for content
                logger.info("Waiting for page content...")
                # Try to find the Download button specifically
                try:
                    await page.wait_for_selector("button.btn-download", timeout=30000)
                except:
                    logger.warning(
                        "Download button not found immediately. Waiting longer..."
                    )
                    await asyncio.sleep(5)

                # Locate the button
                # The button usually has text "Download Excel"
                button = (
                    page.locator("button.btn-download")
                    .filter(has_text="Download Excel")
                    .first
                )

                if await button.count() > 0:
                    logger.info("Found 'Download Excel' button.")

                    doc_info = {
                        "text": "Daily Summary",
                        "title": f"Daily Summary {ticker}",
                        "url": page.url,
                        "expected_type": "xls",  # DFM serves HTML disguised as XLS.
                    }

                    # DFMDownloadManager will download the file.
                    # NOTE: If it detects the "XLS" is actually HTML, it converts it to a valid .xlsx file.
                    # This is why the final output might be .xlsx even if the source was .xls.
                    result = await self.download_manager.download_with_retry(
                        element=button,
                        page=page,
                        doc_info=doc_info,
                        target_dir=target_dir,
                        max_retries=3,
                    )

                    if result:
                        logger.info(
                            f"✓ Successfully downloaded and processed: {result}"
                        )
                    else:
                        logger.error("✗ Download failed.")
                else:
                    logger.warning(
                        "Could not find 'Download Excel' button on the page."
                    )
                    # Take screenshot for debug
                    await page.screenshot(path=f"debug_{ticker}_no_button.png")

            except Exception as e:
                logger.error(f"Error during extraction for {ticker}: {e}")
            finally:
                await browser.close()


if __name__ == "__main__":
    import sys

    # List of tickers to process
    tickers = [
        "AIRARABIA",
        # "DU",
        # "EMAAR",
        # "EMIRATESNBD",
        # "MASQ",
        # "TALABAT",
    ]

    if len(sys.argv) > 1:
        # Check if arg is a ticker
        arg = sys.argv[1]
        if "dfm.ae" in arg:
            # Extract ticker from URL if user pastes URL
            match = re.search(r"company/([^/]+)", arg)
            if match:
                tickers = [match.group(1).upper()]
        else:
            tickers = [arg.upper()]

    async def run_batch():
        extractor = DFMStockExtractor()
        for ticker in tickers:
            await extractor.extract(ticker)

    asyncio.run(run_batch())
