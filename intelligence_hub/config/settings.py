import os
from dotenv import load_dotenv

# Load environment variables and force override
load_dotenv(override=True)

class Settings:
    # API Keys
    SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
    SCRAPER_PROVIDER = os.getenv("SCRAPER_PROVIDER", "scraperapi")  # scraperapi, scrape.do, scrapingbee
    # --- LLM Provider Management ---
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").lower()
    
    # Provider-Specific Native Configurations
    PROVIDER_CONFIGS = {
        "google": {
            "model": "gemini-1.5-flash",
            "embedding": "models/gemini-embedding-001",
        },
        "openai": {
            "model": "gpt-4o",
            "embedding": "text-embedding-3-small",
        },
        "ollama": {
            "model": "llama3",
            "embedding": "nomic-embed-text",
            "base_url": "http://localhost:11434"
        },
        "anthropic": {
            "model": "claude-3-5-sonnet-20240620",
            "embedding": None # Anthropic doesn't have an embedding model yet
        }
    }

    # Auto-resolve settings based on provider, but allow explicit .env overrides
    _native = PROVIDER_CONFIGS.get(LLM_PROVIDER, PROVIDER_CONFIGS["google"])
    
    LLM_MODEL = os.getenv("LLM_MODEL") or _native.get("model")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL") or _native.get("embedding")
    
    # Generic API Key mapping
    LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or LLM_API_KEY
    
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or _native.get("base_url", "http://localhost:11434")

    # --- Other Settings ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    CACHE_TTL_HOURS = 24
    HEADLESS = False
    
    MAX_DOCUMENT_AGE_YEARS = int(os.getenv("MAX_DOCUMENT_AGE_YEARS", "3"))
    ENABLE_DATE_FILTERING = os.getenv("ENABLE_DATE_FILTERING", "true").lower() == "true"

    def validate(self):
        """Validates critical configuration."""
        if not self.SCRAPER_API_KEY:
            print("⚠️ Warning: SCRAPER_API_KEY not found. Scrapers will run in Mock Mode.")
        if self.LLM_PROVIDER != "ollama" and not self.LLM_API_KEY:
             print(f"⚠️ Warning: No API key found for {self.LLM_PROVIDER}. LLM won't work.")
        print(f"📊 Active Config: Provider={self.LLM_PROVIDER} | Model={self.LLM_MODEL} | Embedding={self.EMBEDDING_MODEL}")

config = Settings()