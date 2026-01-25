import os
import json
import logging
from datetime import datetime
from intelligence_hub.config.settings import config

logger = logging.getLogger(__name__)

class StorageManager:
    """
    Manages file storage for scraped data in structured/unstructured formats.
    Structure: ./data/{source}/{format}/{ticker}_{timestamp}.{ext}
    """
    
    @staticmethod
    def save_raw(content: str, source: str, ticker: str, extension: str = "html") -> str:
        """
        Saves raw content (Unstructured).
        """
        directory = os.path.join(config.DATA_DIR, source, "unstructured")
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}.{extension}"
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"Saved raw data to {filepath}")
        return filepath

    @staticmethod
    def save_structured(data: dict, source: str, ticker: str) -> str:
        """
        Saves parsed data (Structured JSON).
        """
        directory = os.path.join(config.DATA_DIR, source, "structured")
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}.json"
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved structured data to {filepath}")
        return filepath
