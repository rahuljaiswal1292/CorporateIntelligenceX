"""Configuration settings"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""

    SCRAPINGBEE_API_KEY: Optional[str] = os.getenv("SCRAPINGBEE_API_KEY")
    MARKET_DATA_TTL: int = int(os.getenv("MARKET_DATA_TTL", "24"))
    DEFAULT_TIMEFRAME_QTR: int = int(os.getenv("DEFAULT_TIMEFRAME_QTR", "12"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./data/chroma_store")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    UI_THEME: str = os.getenv("UI_THEME", "corporate_blue")
    RENDER_JS: bool = True
    COUNTRY_CODE: str = "ae"

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration"""
        if not cls.SCRAPINGBEE_API_KEY:
            raise ValueError("SCRAPINGBEE_API_KEY is required")

config = Config()