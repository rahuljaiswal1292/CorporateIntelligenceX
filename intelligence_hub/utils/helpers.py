"""Helper utilities"""
import logging
import time
from typing import Dict, Any, Optional
from intelligence_hub.config.settings import config

def setup_logging() -> logging.Logger:
    """Configure application logging"""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('intelligence_hub.log')
        ]
    )
    return logging.getLogger(__name__)

def format_currency(amount: float) -> str:
    """Format currency amount"""
    if amount >= 1e9:
        return f"{amount/1e9:.1f}B"
    elif amount >= 1e6:
        return f"{amount/1e6:.1f}M"
    elif amount >= 1e3:
        return f"{amount/1e3:.0f}K"
    return f"{amount:.2f}"

def calculate_growth_rate(current: float, previous: float) -> float:
    """Calculate percentage growth"""
    return ((current - previous) / previous * 100) if previous != 0 else 0.0

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get dictionary value"""
    return data.get(key, default) if isinstance(data, dict) else default

def validate_ticker_format(ticker: str) -> bool:
    """Validate ticker format"""
    return ticker.isalnum() and ticker.isupper() and len(ticker) <= 10

def normalize_company_name(name: str) -> str:
    """Normalize company name"""
    return name.strip().title()

def is_data_stale(last_update: float, ttl_hours: int = None) -> bool:
    """Check if data exceeds TTL"""
    ttl = ttl_hours or config.MARKET_DATA_TTL
    return time.time() - last_update > ttl * 3600

def create_progress_message(step: str, status: str) -> str:
    """Create progress message"""
    emoji = "✅" if status == "complete" else "🔄"
    return f"{emoji} {step}: {status}"