import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    # API Keys
    SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
    SCRAPER_PROVIDER = os.getenv(
        "SCRAPER_PROVIDER", "scraperapi"
    )  # scraperapi, scrape.do, scrapingbee

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

    # Paths
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    DATA_DIR = os.path.join(BASE_DIR, "data")

    # Caching
    CACHE_TTL_HOURS = 24  # Stale after 1 day
    # Playwright
    HEADLESS = False  # Set to False to bypass cloudflare/bot detection

    # Document Filtering
    MAX_DOCUMENT_AGE_YEARS = int(os.getenv("MAX_DOCUMENT_AGE_YEARS", "3"))
    ENABLE_DATE_FILTERING = os.getenv("ENABLE_DATE_FILTERING", "true").lower() == "true"

    # Known Ticker Map (Static Overrides)
    KNOWN_TICKER_MAP = {
        "emaar": {
            "ticker": "EMAAR",
            "exchange": "DFM",
            "name": "Emaar Properties",
            "website": "https://www.emaar.com",
        },
        "lulu": {
            "ticker": "LULU",
            "exchange": "ADX",
            "name": "Lulu Retail Holdings",
            "website": "https://luluretail.com",
        },
        "mashreq": {
            "ticker": "MASQ",
            "exchange": "DFM",
            "name": "Mashreq Bank",
            "website": "https://www.mashreqbank.com",
        },
        "nbd": {
            "ticker": "ENBD",
            "exchange": "DFM",
            "name": "Emirates NBD",
            "website": "https://www.emiratesnbd.com",
        },
        "e&": {
            "ticker": "EAND",
            "exchange": "ADX",
            "name": "e& (Etisalat)",
            "website": "https://www.eand.com",
        },
        "ajman": {
            "ticker": "AJMANBANK",
            "exchange": "DFM",
            "name": "Ajman Bank",
            "website": "https://www.ajmanbank.ae",
        },
    }

    def validate(self):
        """Validates critical configuration."""
        if not self.SCRAPER_API_KEY:
            print(
                "⚠️ Warning: SCRAPER_API_KEY not found. Scrapers will run in Mock Mode."
            )


config = Settings()
