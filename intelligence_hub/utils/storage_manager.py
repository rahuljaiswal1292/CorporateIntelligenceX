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
        Structure: ./data/{source}/{ticker}/unstructured/{ticker}_{timestamp}.{ext}
        """
        directory = os.path.join(config.DATA_DIR, source, ticker, "unstructured")
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}.{extension}"
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"Saved raw data to {filepath}")
        return filepath

    @staticmethod
    def save_page_content(content: str, source: str, ticker: str, page_type: str, 
                         content_type: str = "html", filename_suffix: str = "") -> str:
        """
        Saves page content organized by page type.
        Structure: ./data/{source}/{ticker}/{page_type}/{content_type}/{ticker}_page.{ext}
        
        Args:
            content: Content to save
            source: Data source (adx, dfm, etc.)
            ticker: Company ticker
            page_type: Page type (overview, financial_reports, disclosures, news, etc.)
            content_type: Type of content (html, json, md)
            filename_suffix: Optional suffix for filename (e.g., "profile", "metrics")
        """
        directory = os.path.join(config.DATA_DIR, source, ticker, page_type, content_type)
        os.makedirs(directory, exist_ok=True)
        
        # Determine extension
        if content_type == "json":
            ext = "json"
            # JSON files keep timestamp as they represent timestamped data snapshots
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = f"_{filename_suffix}" if filename_suffix else ""
            filename = f"{ticker}_{timestamp}{suffix}.{ext}"
        elif content_type == "md":
            ext = "md"
            # Static filename for HTML/MD to avoid duplicates on multiple runs
            suffix = f"_{filename_suffix}" if filename_suffix else "_page_clean"
            filename = f"{ticker}{suffix}.{ext}"
        else:
            ext = "html"
            # Static filename for HTML/MD to avoid duplicates on multiple runs
            suffix = f"_{filename_suffix}" if filename_suffix else "_page"
            filename = f"{ticker}{suffix}.{ext}"
        
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"Saved {content_type} to {filepath}")
        return filepath

    @staticmethod
    def save_document(content: bytes, source: str, ticker: str, category: str, filename: str) -> str:
        """
        Saves a downloaded document (PDF, DOCX, etc.) to a categorized folder.
        Structure: ./data/{source}/{ticker}/{category}/{filename}
        """
        # Santize filename
        filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
        
        directory = os.path.join(config.DATA_DIR, source, ticker, category)
        os.makedirs(directory, exist_ok=True)
        
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "wb") as f:
            f.write(content)
            
        logger.info(f"Saved document to {filepath}")
        return filepath

    @staticmethod
    def save_page_document(content: bytes, source: str, ticker: str, page_type: str, 
                          filename: str) -> str:
        """
        Saves a document organized by page type.
        Structure: ./data/{source}/{ticker}/{page_type}/structured/{filename}
        
        All documents (PDF, DOCX, XLSX, etc.) go to structured/ directory.
        
        Args:
            content: Binary content of document
            source: Data source (adx, dfm, etc.)
            ticker: Company ticker
            page_type: Page type (overview, financial_reports, disclosures, news, etc.)
            filename: Document filename
        """
        # Sanitize filename
        filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).rstrip()
        
        # All documents go to structured/ directory
        directory = os.path.join(config.DATA_DIR, source, ticker, page_type, "structured")
        os.makedirs(directory, exist_ok=True)
        
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "wb") as f:
            f.write(content)
            
        logger.info(f"Saved document to {filepath}")
        return filepath

    @staticmethod
    def save_structured(data: dict, source: str, ticker: str) -> str:
        """
        Saves parsed data (Structured JSON).
        Structure: ./data/{source}/{ticker}/structured/{ticker}_{timestamp}.json
        """
        directory = os.path.join(config.DATA_DIR, source, ticker, "structured")
        os.makedirs(directory, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{ticker}_{timestamp}.json"
        filepath = os.path.join(directory, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved structured data to {filepath}")
        return filepath
