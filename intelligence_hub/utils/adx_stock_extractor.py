import asyncio
import os
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from playwright.async_api import async_playwright, Response, Page

try:
    from intelligence_hub.config.settings import config
except ImportError:
    config = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ADXStockExtractor")


class ADXStockExtractor:
    def __init__(self, output_path: str = None):
        self.output_path = output_path
        self.target_symbol = ""
        self.captured_data = []
        self.discovered_api_url = ""
        self.processed_df = None
        self.request_headers = {}

    async def extract(self, url: str):
        """Main extraction flow."""
        self.target_url = url
        self.symbol = self._extract_symbol_from_url(url)
        self.target_symbol = self.symbol  # Ensure both are set
        logger.info(f"Starting extraction for URL: {url}")
        logger.info(f"Target Symbol: {self.symbol}")

        async with async_playwright() as p:
            # Use stealthier browser launch
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--window-size=1920,1080",
                    "--disable-infobars",
                ],
            )
            # Realistic context
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )

            # Additional evasion: mask navigator.webdriver
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            page = await context.new_page()

            # Network listener to capture the API call
            page.on("request", self._handle_request)
            page.on("response", self._handle_response)

            try:
                logger.info(f"Navigating to {url}...")
                # increased timeout for Cloudflare/heavy page
                await page.goto(url, wait_until="load", timeout=60000)

                # Wait for some content to ensure it's not a block page
                try:
                    await page.wait_for_selector("text=ADX", timeout=10000)
                except:
                    title = await page.title()
                    if "Attention Required" in title or "Cloudflare" in title:
                        logger.error("Blocked by Cloudflare challenge.")
                        await page.screenshot(path="cloudflare_block.png")
                        await browser.close()
                        return

                # Scroll to bring the chart into view
                await page.evaluate("window.scrollTo(0, 800)")
                await asyncio.sleep(3)

                # Try to trigger 3-month history via interaction
                # await self._trigger_3month_history(page)

                # If we discovered the API, fetch 3 months (100 records)
                if self.discovered_api_url:
                    logger.info(f"Using discovered API: {self.discovered_api_url}")

                    # Ensure full_url is constructed safely
                    full_url = self.discovered_api_url
                    if "recentTrades" in full_url:
                        # recentTrades might not support recordCount or needs different handling
                        pass
                    elif "recordCount=" not in full_url:
                        if "?" in full_url:
                            full_url += "&recordCount=100"
                        else:
                            full_url += "?recordCount=100"

                    logger.info(
                        f"Fetching 3-month data via request context: {full_url}"
                    )
                    try:
                        response = await page.context.request.get(
                            full_url, headers=self.request_headers
                        )
                        if response.ok:
                            history_json = await response.json()
                            results = history_json.get("response", {}).get(
                                "results", []
                            )
                            if results:
                                logger.info(
                                    f"Successfully captured {len(results)} historical records."
                                )
                                self.captured_data = []  # Reset to use full history
                                self._normalize_list_data(results)
                        else:
                            logger.error(
                                f"Request context fetch failed: {response.status} {response.status_text}"
                            )
                    except Exception as e:
                        logger.error(
                            f"Failed to fetch history via request context: {e}"
                        )

                # If still no data, check for page-level scripts (NEXT_DATA)
                if not self.captured_data:
                    logger.info("Checking __NEXT_DATA__ for embedded chart data...")
                    next_data = await page.evaluate(
                        "() => JSON.stringify(window.__NEXT_DATA__ || {})"
                    )
                    if next_data:
                        try:
                            self._handle_json_content(
                                json.loads(next_data), "NEXT_DATA"
                            )
                        except:
                            pass

                if not self.captured_data:
                    logger.warning("No chart data captured. Waiting a bit more...")
                    await asyncio.sleep(10)

                # Final processing
                if self.captured_data:
                    self._process_data()
                    self._save_to_csv()
                    logger.info("Extraction complete.")
                else:
                    logger.error("Failed to capture any chart data.")

            except Exception as e:
                logger.error(f"Error during extraction: {e}")
            finally:
                await browser.close()

    async def extract_from_page(self, page: Page, url: str):
        """
        Extract chart data using an existing page (no new browser instance).
        This is more efficient when called from an existing scraper session.
        """
        self.target_url = url
        self.symbol = self._extract_symbol_from_url(url)
        self.target_symbol = self.symbol
        logger.info(f"Starting extraction from existing page for: {self.symbol}")

        try:
            # Setup network listeners
            page.on("request", self._handle_request)
            page.on("response", self._handle_response)

            # The page is already on the orderbook URL, so we don't need to navigate
            # Just wait for content to load
            logger.info("Waiting for chart content to load...")
            await page.wait_for_timeout(2000)

            # Scroll to bring the chart into view
            await page.evaluate("window.scrollTo(0, 800)")
            await asyncio.sleep(3)

            # Try to trigger 3-month history via interaction
            await self._trigger_3month_history(page)

            # If we discovered the API, fetch 3 months (100 records)
            if self.discovered_api_url:
                logger.info(f"Using discovered API: {self.discovered_api_url}")

                # Ensure full_url is constructed safely
                full_url = self.discovered_api_url
                if "recentTrades" in full_url:
                    pass
                elif "recordCount=" not in full_url:
                    if "?" in full_url:
                        full_url += "&recordCount=100"
                    else:
                        full_url += "?recordCount=100"

                logger.info(f"Fetching 3-month data via request context: {full_url}")
                try:
                    response = await page.context.request.get(
                        full_url, headers=self.request_headers
                    )
                    if response.ok:
                        history_json = await response.json()
                        results = history_json.get("response", {}).get("results", [])
                        if results:
                            logger.info(
                                f"Successfully captured {len(results)} historical records."
                            )
                            self.captured_data = []  # Reset to use full history
                            self._normalize_list_data(results)
                    else:
                        logger.error(
                            f"Request context fetch failed: {response.status} {response.status_text}"
                        )
                except Exception as e:
                    logger.error(f"Failed to fetch history via request context: {e}")

            # If still no data, check for page-level scripts (NEXT_DATA)
            if not self.captured_data:
                logger.info("Checking __NEXT_DATA__ for embedded chart data...")
                next_data = await page.evaluate(
                    "() => JSON.stringify(window.__NEXT_DATA__ || {})"
                )
                if next_data:
                    try:
                        self._handle_json_content(json.loads(next_data), "NEXT_DATA")
                    except:
                        pass

            if not self.captured_data:
                logger.warning("No chart data captured. Waiting a bit more...")
                await asyncio.sleep(10)

            # Final processing
            if self.captured_data:
                self._process_data()
                self._save_to_csv()
                logger.info("Extraction complete.")
            else:
                logger.error("Failed to capture any chart data.")

        except Exception as e:
            logger.error(f"Error during extraction from page: {e}")
            import traceback

            traceback.print_exc()

    def _extract_symbol_from_url(self, url: str) -> str:
        match = re.search(r"symbols=([^&]+)", url)
        return match.group(1).upper() if match else "UNKNOWN"

    async def _handle_request(self, request):
        """Intercepts requests to capture headers."""
        try:
            url = request.url
            if "recentTrades" in url:
                headers = request.headers
                logger.info(f"CAPTURED REQUEST HEADERS for {url}")
                # Log to a file for inspection
                with open("last_headers.json", "w") as f:
                    json.dump(dict(headers), f, indent=2)
                self.request_headers = headers
        except:
            pass

    async def _handle_response(self, response: Response):
        """Intercepts and parses network responses."""
        try:
            url = response.url
            content_type = response.headers.get("content-type", "").lower()

            # Skip noise
            if any(
                ext in url
                for ext in [
                    ".css",
                    ".png",
                    ".jpg",
                    ".js",
                    "google-analytics",
                    "sprinklr",
                ]
            ):
                return

            if "json" in content_type:
                try:
                    text_content = await response.text()
                    data = json.loads(text_content)
                    self._handle_json_content(data, url)
                except:
                    pass
        except:
            pass

    async def _trigger_3month_history(self, page: Page):
        """Attempts to click the '3M' button on the TradingView chart."""
        logger.info("Attempting to trigger 3-month history via chart interaction...")
        try:
            # 1. Identify if chart is in an iframe
            iframes = page.frames
            target_frame = None
            for frame in iframes:
                if "tradingview" in frame.url.lower():
                    target_frame = frame
                    break

            context = target_frame if target_frame else page
            if not context:
                logger.error("No valid context (page or frame) for interaction.")
                return

            # 2. Heuristic selectors for the '3M' button
            selectors = [
                "div:has-text('3M')",
                "button:has-text('3M')",
                "div[data-range='3M']",
                ".button-qw_9_P-4:has-text('3M')",  # Common TV class pattern
                "text=3M",
            ]

            for selector in selectors:
                try:
                    btn = context.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        logger.info(f"Clicking '3M' button using selector: {selector}")
                        await btn.click()
                        await asyncio.sleep(3)
                        return
                except:
                    continue

            logger.warning("Could not find '3M' button via standard selectors.")

            # 3. Last resort: JS click to find specific text in all elements
            await context.evaluate(
                """
                () => {
                    const divs = Array.from(document.querySelectorAll('div, button'));
                    const btn = divs.find(d => d.innerText.trim() === '3M');
                    if (btn) btn.click();
                }
            """
            )
            await asyncio.sleep(3)

        except Exception as e:
            logger.warning(f"Interactive trigger failed: {e}")

    def _handle_json_content(self, data, url: str):
        """Heuristics to find OHLC data in JSON."""
        # 1. TradingView format {t:[], o:[], ...}
        if isinstance(data, dict):
            # Check top level
            if "t" in data and "c" in data and isinstance(data["t"], list):
                self._normalize_tv_data(data)
                return

            # Check 'response.results' (ADX pattern)
            resp = data.get("response")
            if isinstance(resp, dict):
                results = resp.get("results")
                if isinstance(results, list) and len(results) > 0:
                    # Look for ADX specific keys: openPrice, lastPrice, tradeDate, dateTime
                    adx_keys = [
                        "open",
                        "close",
                        "date",
                        "openPrice",
                        "lastPrice",
                        "tradeDate",
                        "dateTime",
                    ]
                    if any(k in results[0] for k in adx_keys):
                        if "recentTrades" in url or "marketwatch" in url:
                            self.discovered_api_url = url
                        self._normalize_list_data(results)
                        return

            # Check for nested data keys
            for key in ["data", "series", "chart", "d"]:
                val = data.get(key)
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    adx_keys = [
                        "open",
                        "close",
                        "date",
                        "openPrice",
                        "lastPrice",
                        "tradeDate",
                        "dateTime",
                    ]
                    if any(k in val[0] for k in adx_keys):
                        self._normalize_list_data(val)
                        return
                elif isinstance(val, dict):
                    if "t" in val and "c" in val:
                        self._normalize_tv_data(val)
                        return

    def _normalize_tv_data(self, data: dict):
        """Normalizes TradingView UDF format."""
        try:
            # Common TV keys: t (time), o (open), h (high), l (low), c (close), v (volume)
            times = data.get("t")
            opens = data.get("o")
            highs = data.get("h")
            lows = data.get("l")
            closes = data.get("c")
            volumes = data.get("v")

            if not times or not opens:
                return

            for i in range(len(times)):
                dt = datetime.fromtimestamp(times[i])
                self.captured_data.append(
                    {
                        "Date": dt.strftime("%Y-%m-%d"),
                        "Open": opens[i],
                        "High": highs[i],
                        "Low": lows[i],
                        "Close": closes[i],
                        "Volume": volumes[i] if volumes else 0,
                        "Trades": 0,
                        "Value": 0,
                        "Previous": 0,
                        "Last": closes[i],
                    }
                )
            logger.info(f"Normalized {len(times)} TradingView records.")
        except Exception as e:
            logger.error(f"Failed to normalize TV data: {e}")

    def _normalize_list_data(self, data: list):
        """Convert list of dicts to standard list, handling ADX key variations."""
        for item in data:
            # Handle variations in keys
            date_val = (
                item.get("date")
                or item.get("time")
                or item.get("tradeDate")
                or item.get("dateTime")
            )
            close_val = (
                item.get("close")
                or item.get("last")
                or item.get("lastPrice")
                or item.get("price")
            )
            open_val = item.get("open") or item.get("openPrice")
            high_val = item.get("high") or item.get("highPrice")
            low_val = item.get("low") or item.get("lowPrice")
            volume_val = item.get("volume") or item.get("quantity") or item.get("qty")

            entry = {
                "Date": date_val,
                "Open": open_val,
                "High": high_val,
                "Low": low_val,
                "Close": close_val,
                "Volume": volume_val,
                "Trades": item.get("trades") or item.get("tradeCount") or 0,
                "Value": item.get("value") or item.get("totalTurnover") or 0,
            }
            if entry["Date"] and entry["Close"] is not None:
                self.captured_data.append(entry)

    def _process_data(self):
        """Clean, filter, and calculate derived columns."""
        if not self.captured_data:
            logger.warning("No data to process.")
            return

        df = pd.DataFrame(self.captured_data)
        if "Date" not in df.columns:
            logger.error(
                f"Captured data missing 'Date' column. Columns found: {df.columns.tolist()}"
            )
            return

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").drop_duplicates("Date")

        # Filter: last 3 months
        three_months_ago = datetime.now() - timedelta(days=90)
        df = df[df["Date"] >= three_months_ago]

        # Calculate Change and %
        df["Previous"] = df["Close"].shift(1)
        df["Change"] = df["Close"] - df["Previous"]
        df["Change %"] = (df["Change"] / df["Previous"]) * 100

        # Round to 2 decimal places
        price_cols = [
            "Open",
            "High",
            "Low",
            "Close",
            "Previous",
            "Change",
            "Change %",
            "Value",
        ]
        df[price_cols] = df[price_cols].round(2)

        # Last price (current close)
        df["Last"] = df["Close"]

        # Sort back to descending for display if needed, but standard is ascending
        self.processed_df = df.reset_index(drop=True)

    def _save_to_csv(self):
        """Save results to CSV only."""
        if self.processed_df is None or self.processed_df.empty:
            logger.warning("Processed dataframe is empty, skipping save.")
            return

        # Use absolute path from config if available
        if config:
            base_dir = os.path.join(
                config.DATA_DIR, "adx", self.target_symbol, "orderbook", "structured"
            )
        else:
            base_dir = f"data/adx/{self.target_symbol}/orderbook/structured"

        os.makedirs(base_dir, exist_ok=True)

        # Save CSV only
        csv_path = os.path.join(base_dir, f"{self.target_symbol}_chart_data.csv")
        self.processed_df.to_csv(csv_path, index=False, float_format="%.2f")
        logger.info(f"Saved {len(self.processed_df)} rows to {csv_path}")


if __name__ == "__main__":
    import sys

    # Configure logging for standalone run
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # List of tickers to process
    tickers = [
        "ADNHC",
        "ADNOCGAS",
        "ALDAR",
        "ALPHADATA",
        "EAND",
        "FAB",
        "LULU",
    ]

    # Allow override from command line
    if len(sys.argv) > 1:
        # If argument is a URL, extract ticker from it
        if "symbols=" in sys.argv[1]:
            import re

            match = re.search(r"symbols=([^&]+)", sys.argv[1])
            if match:
                tickers = [match.group(1).upper()]
        else:
            # Otherwise treat as ticker symbol
            tickers = [sys.argv[1].upper()]

    async def run_batch():
        """Process all tickers in batch"""
        total = len(tickers)
        logger.info(
            f"Starting batch extraction for {total} tickers: {', '.join(tickers)}"
        )
        logger.info("=" * 80)

        for idx, ticker in enumerate(tickers, 1):
            logger.info(f"\n[{idx}/{total}] Processing {ticker}...")
            logger.info("-" * 80)

            # url = f"https://www.adx.ae/main-market/company-profile/overview?symbols={ticker}"
            # extractor = ADXStockExtractor()

            # try:
            #     await extractor.extract(url)
            #     logger.info(f"✓ Successfully completed {ticker}")
            # except Exception as e:
            #     logger.error(f"✗ Failed to extract {ticker}: {e}")

            # # Small delay between tickers to avoid overwhelming the server
            # if idx < total:
            #     await asyncio.sleep(2)

        # Parallel Execution
        sem = asyncio.Semaphore(3)  # Limit concurrency

        async def process(ticker):
            async with sem:
                url = f"https://www.adx.ae/main-market/company-profile/overview?symbols={ticker}"
                extractor = ADXStockExtractor()
                try:
                    await extractor.extract(url)
                    logger.info(f"✓ Successfully completed {ticker}")
                except Exception as e:
                    logger.error(f"✗ Failed to extract {ticker}: {e}")

        logger.info("Executing in parallel (max 3)...")
        tasks = [process(t) for t in tickers]
        await asyncio.gather(*tasks)

        logger.info("\n" + "=" * 80)
        logger.info(f"Batch extraction complete! Processed {total} tickers.")
        logger.info("=" * 80)

    asyncio.run(run_batch())
