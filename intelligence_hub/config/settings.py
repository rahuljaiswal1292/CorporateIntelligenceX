import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # API Keys
    SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    # Caching
    CACHE_TTL_HOURS = 24  # Stale after 1 day
    
    # Pinecone
    PINECONE_INDEX_NAME = "corporate-intelligence"
    PINECONE_ENV = "gcp-starter"

    # Known Ticker Map (Static Overrides)
    KNOWN_TICKER_MAP = {
        "emaar": {"ticker": "EMAAR", "exchange": "DFM", "name": "Emaar Properties"},
        "lulu": {"ticker": "LULU", "exchange": "ADX", "name": "Lulu Retail Holdings"},
        "mashreq": {"ticker": "MASQ", "exchange": "DFM", "name": "Mashreq Bank"},
        "nbd": {"ticker": "ENBD", "exchange": "DFM", "name": "Emirates NBD"},
        "e&": {"ticker": "EAND", "exchange": "ADX", "name": "e& (Etisalat)"},
        "ajman": {"ticker": "AJMANBANK", "exchange": "DFM", "name": "Ajman Bank"}
    }

    def validate(self):
        """Validates critical configuration."""
        if not self.SCRAPINGBEE_API_KEY:
            print("⚠️ Warning: SCRAPINGBEE_API_KEY not found. Scrapers will run in Mock Mode.")
        if not self.PINECONE_API_KEY:
             print("⚠️ Warning: PINECONE_API_KEY not found. Vector DB will run in Mock Mode.")

config = Settings()