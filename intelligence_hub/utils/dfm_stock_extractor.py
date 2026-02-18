import asyncio
import os
import logging
import sys
import re
from typing import Optional, List
import pandas as pd
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
    Converts downloaded Excel files to CSV.
    """

    def __init__(self):
        self.download_manager = OverwritingDFMDownloadManager()
        self.browser: Optional[Browser] = None

    async def extract_from_page(
        self, page: Page, ticker: str, target_dir: str = None
    ) -> bool:
        """
        Extract data using an existing page object.
        Assumes page is already navigated to the target URL or is the target page.
        """
        ticker = ticker.upper()
        logger.info(f"Extracting Daily Summary for {ticker} from current page...")

        if not target_dir:
            if DATA_DIR:
                target_dir = os.path.join(
                    DATA_DIR, "dfm", ticker, "daily_summary", "structured"
                )
            else:
                target_dir = os.path.join(
                    "data", "dfm", ticker, "daily_summary", "structured"
                )

        os.makedirs(target_dir, exist_ok=True)

        try:
            # Check for "Loading..."
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            # Wait for content
            # Try to find the Download button specifically
            try:
                await page.wait_for_selector("button.btn-download", timeout=10000)
            except:
                logger.warning(
                    "Download button not found immediately. Checking frames/content..."
                )

            # Locate the button
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

                result = await self.download_manager.download_with_retry(
                    element=button,
                    page=page,
                    doc_info=doc_info,
                    target_dir=target_dir,
                    max_retries=3,
                )

                if result:
                    # Convert to CSV if it's an Excel file
                    if result.lower().endswith((".xls", ".xlsx")):
                        try:
                            logger.info(
                                f"Attempting to convert {os.path.basename(result)} to CSV..."
                            )

                            # Ensure openpyxl is available (critical for .xlsx)
                            try:
                                import openpyxl
                            except ImportError:
                                logger.error(
                                    "Module 'openpyxl' not found! This is required for Excel files. Please run: pip install openpyxl"
                                )
                                # Try fallback using only pandas basic functionality (might work for .xls if xlrd >= 2.0.1 installed)

                            # Attempt to read Excel file
                            # DFM files can be tricky (HTML disguised as XLS, or real XLSX)
                            try:
                                df = pd.read_excel(result)
                            except Exception as e_read:
                                logger.warning(
                                    f"Standard read_excel failed for {result}: {e_read}. Attempting read_html fallback (common for DFM .xls)..."
                                )
                                # Fallback for HTML content with .xls extension
                                try:
                                    dfs = pd.read_html(result)
                                    if dfs:
                                        df = dfs[0]
                                    else:
                                        raise ValueError(
                                            "No tables found in HTML content"
                                        )
                                except Exception as e_html:
                                    logger.error(
                                        f"Both read_excel and read_html failed: {e_html}"
                                    )
                                    raise e_read  # Re-raise original error if fallback fails

                            # Define CSV path
                            csv_path = os.path.splitext(result)[0] + ".csv"

                            # Save as CSV
                            df.to_csv(csv_path, index=False)
                            logger.info(
                                f"✓ Converted to CSV: {os.path.basename(csv_path)}"
                            )

                            # Remove original Excel file
                            try:
                                os.remove(result)
                                logger.info(
                                    f"Removed original file: {os.path.basename(result)}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Could not remove original file {result}: {e}"
                                )

                        except Exception as e:
                            logger.error(
                                f"Failed to convert Excel to CSV: {e}", exc_info=True
                            )
                            logger.warning(f"Kept original file as backup: {result}")
                            # We still consider it a success if download happened,
                            # but warn about conversion failure.

                    logger.info(f"✓ Successfully downloaded and processed: {result}")
                    return True
                else:
                    logger.error("✗ Download failed.")
                    return False
            else:
                logger.warning("Could not find 'Download Excel' button on the page.")
                try:
                    await page.screenshot(path=f"debug_{ticker}_no_button.png")
                except:
                    pass
                return False

        except Exception as e:
            logger.error(f"Error during extraction for {ticker}: {e}")
            return False

    async def extract(self, ticker: str):
        """
        Main extraction flow for a single ticker (Standalone Mode).
        Launches its own browser.
        """
        ticker = ticker.upper()
        url = f"https://www.dfm.ae/the-exchange/market-information/company/{ticker}/trading/daily-summary"

        logger.info(f"Starting standalone extraction for {ticker} at {url}")

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,
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

            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            try:
                logger.info(f"Navigating to {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Use shared extraction logic
                await self.extract_from_page(page, ticker)

            except Exception as e:
                logger.error(f"Error during extraction for {ticker}: {e}")
            finally:
                await browser.close()


if __name__ == "__main__":
    # List of tickers to process
    tickers = [
        "AIRARABIA",
        # "DU",
        # "EMAAR",
        # "EMIRATESNBD",
        # "MASQ",
        # "TALABAT",
    ]

    import sys

    if len(sys.argv) > 1:
        # Check if arg is a ticker
        arg = sys.argv[1]
        if "dfm.ae" in arg:
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
