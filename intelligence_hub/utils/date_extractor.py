"""
Date Extraction Utility

Extracts publication dates from documents to filter files by age.
Supports multiple strategies when filenames don't indicate dates.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from email.utils import parsedate_to_datetime

logger = logging.getLogger("DateExtractor")


class DateExtractor:
    """Extract and validate document dates from multiple sources."""
    
    # Common date patterns in URLs and filenames
    DATE_PATTERNS = [
        r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # 2024-01-15 or 2024/01/15
        r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # 15-01-2024 or 15/01/2024
        r'(\d{4})(\d{2})(\d{2})',              # 20240115
        r'[Qq](\d)[_\s-]?(\d{4})',             # Q1 2024, Q1_2024
        r'(\d{4})[_\s-]?[Qq](\d)',             # 2024 Q1, 2024_Q1
        r'[Ff][Yy](\d{4})',                    # FY2024
        r'(\d{4})',                            # Just year: 2024
    ]
    
    # Month names for text parsing
    MONTHS = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    @staticmethod
    def extract_from_url(url: str) -> Optional[datetime]:
        """
        Extract date from URL or filename.
        
        Args:
            url: Document URL
            
        Returns:
            datetime object if date found, None otherwise
        """
        for pattern in DateExtractor.DATE_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    # Handle different patterns
                    if 'Q' in pattern or 'q' in pattern:
                        # Quarter pattern
                        if len(groups) == 2:
                            if groups[0].isdigit() and len(groups[0]) == 4:
                                year, quarter = int(groups[0]), int(groups[1])
                            else:
                                quarter, year = int(groups[0]), int(groups[1])
                            month = (quarter - 1) * 3 + 1
                            return datetime(year, month, 1)
                    
                    elif len(groups) == 3:
                        # Full date pattern
                        if len(groups[0]) == 4:
                            # YYYY-MM-DD
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:
                            # DD-MM-YYYY
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        return datetime(year, month, day)
                    
                    elif len(groups) == 1:
                        # Just year
                        year = int(groups[0])
                        if 2000 <= year <= 2100:
                            return datetime(year, 1, 1)
                
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse date from URL pattern: {e}")
                    continue
        
        return None
    
    @staticmethod
    def extract_from_text(text: str) -> Optional[datetime]:
        """
        Extract date from link text or nearby content.
        
        Args:
            text: Text content to parse
            
        Returns:
            datetime object if date found, None otherwise
        """
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Try URL patterns first
        date = DateExtractor.extract_from_url(text)
        if date:
            return date
        
        # Look for month + year patterns
        for month_name, month_num in DateExtractor.MONTHS.items():
            pattern = rf'\b{month_name}\s+(\d{{4}})\b'
            match = re.search(pattern, text_lower)
            if match:
                year = int(match.group(1))
                if 2000 <= year <= 2100:
                    return datetime(year, month_num, 1)
        
        # Look for year + month patterns
        for month_name, month_num in DateExtractor.MONTHS.items():
            pattern = rf'\b(\d{{4}})\s+{month_name}\b'
            match = re.search(pattern, text_lower)
            if match:
                year = int(match.group(1))
                if 2000 <= year <= 2100:
                    return datetime(year, month_num, 1)
        
        return None
    
    @staticmethod
    def extract_from_headers(headers: Dict[str, str]) -> Optional[datetime]:
        """
        Extract date from HTTP response headers.
        
        Args:
            headers: HTTP response headers
            
        Returns:
            datetime object if date found, None otherwise
        """
        if not headers:
            return None
        
        # Try Last-Modified header
        last_modified = headers.get('last-modified') or headers.get('Last-Modified')
        if last_modified:
            try:
                return parsedate_to_datetime(last_modified)
            except Exception as e:
                logger.debug(f"Failed to parse Last-Modified header: {e}")
        
        # Try Date header
        date_header = headers.get('date') or headers.get('Date')
        if date_header:
            try:
                return parsedate_to_datetime(date_header)
            except Exception as e:
                logger.debug(f"Failed to parse Date header: {e}")
        
        return None
    
    @staticmethod
    def extract_from_pdf_content(file_content: bytes) -> Optional[datetime]:
        """
        Extract date from PDF content (first page scan).
        
        Args:
            file_content: PDF file content as bytes
            
        Returns:
            datetime object if date found, None otherwise
        """
        try:
            import PyPDF2
            from io import BytesIO
            
            # Read PDF
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            
            # Check metadata first
            if pdf_reader.metadata:
                creation_date = pdf_reader.metadata.get('/CreationDate')
                if creation_date:
                    # PDF dates are in format: D:YYYYMMDDHHmmSS
                    date_match = re.search(r'D:(\d{4})(\d{2})(\d{2})', str(creation_date))
                    if date_match:
                        year, month, day = map(int, date_match.groups())
                        return datetime(year, month, day)
            
            # Scan first page text
            if len(pdf_reader.pages) > 0:
                first_page_text = pdf_reader.pages[0].extract_text()
                date = DateExtractor.extract_from_text(first_page_text[:1000])  # First 1000 chars
                if date:
                    logger.debug(f"Extracted date from PDF first page: {date}")
                    return date
        
        except ImportError:
            logger.warning("PyPDF2 not installed. Cannot scan PDF content for dates.")
        except Exception as e:
            logger.debug(f"Failed to extract date from PDF content: {e}")
        
        return None
    
    @staticmethod
    def extract_from_excel_content(file_content: bytes) -> Optional[datetime]:
        """
        Extract date from Excel content (first sheet scan).
        
        Args:
            file_content: Excel file content as bytes
            
        Returns:
            datetime object if date found, None otherwise
        """
        try:
            import openpyxl
            from io import BytesIO
            
            # Read Excel
            wb = openpyxl.load_workbook(BytesIO(file_content), read_only=True, data_only=True)
            
            # Check first sheet
            if wb.worksheets:
                sheet = wb.worksheets[0]
                
                # Scan first few rows for dates
                for row in sheet.iter_rows(max_row=10, max_col=10):
                    for cell in row:
                        if cell.value:
                            # Check if cell contains date
                            if isinstance(cell.value, datetime):
                                return cell.value
                            
                            # Try to parse text
                            cell_text = str(cell.value)
                            date = DateExtractor.extract_from_text(cell_text)
                            if date:
                                logger.debug(f"Extracted date from Excel cell: {date}")
                                return date
        
        except ImportError:
            logger.warning("openpyxl not installed. Cannot scan Excel content for dates.")
        except Exception as e:
            logger.debug(f"Failed to extract date from Excel content: {e}")
        
        return None
    
    @staticmethod
    def is_within_years(date: Optional[datetime], years: int = 3) -> bool:
        """
        Check if date is within specified years from now.
        
        Args:
            date: Date to check (None means unknown, returns True to be safe)
            years: Number of years threshold
            
        Returns:
            True if date is within years or unknown, False if too old
        """
        if date is None:
            # If date unknown, assume it's recent (don't filter out)
            return True
        
        cutoff = datetime.now() - timedelta(days=years * 365)
        return date >= cutoff
    
    @staticmethod
    def extract_document_date(
        url: str,
        link_text: str = None,
        nearby_text: str = None,
        response_headers: Dict[str, str] = None,
        file_content: bytes = None,
        file_extension: str = None
    ) -> Optional[datetime]:
        """
        Extract publication date from multiple sources (priority order).
        
        Args:
            url: Document URL
            link_text: Text of the link element
            nearby_text: Text near the link (e.g., date spans)
            response_headers: HTTP response headers
            file_content: Downloaded file content (for PDF/Excel scanning)
            file_extension: File extension (pdf, xls, xlsx)
            
        Returns:
            datetime object if date found, None otherwise
        """
        # Strategy 1: Check nearby text (most reliable)
        if nearby_text:
            date = DateExtractor.extract_from_text(nearby_text)
            if date:
                logger.debug(f"Extracted date from nearby text: {date}")
                return date
        
        # Strategy 2: Check link text
        if link_text:
            date = DateExtractor.extract_from_text(link_text)
            if date:
                logger.debug(f"Extracted date from link text: {date}")
                return date
        
        # Strategy 3: Check URL
        date = DateExtractor.extract_from_url(url)
        if date:
            logger.debug(f"Extracted date from URL: {date}")
            return date
        
        # Strategy 4: Check HTTP headers
        if response_headers:
            date = DateExtractor.extract_from_headers(response_headers)
            if date:
                logger.debug(f"Extracted date from headers: {date}")
                return date
        
        # Strategy 5: Scan file content (fallback)
        if file_content and file_extension:
            ext = file_extension.lower().replace('.', '')
            
            if ext == 'pdf':
                date = DateExtractor.extract_from_pdf_content(file_content)
                if date:
                    logger.info(f"Extracted date from PDF content: {date}")
                    return date
            
            elif ext in ['xls', 'xlsx']:
                date = DateExtractor.extract_from_excel_content(file_content)
                if date:
                    logger.info(f"Extracted date from Excel content: {date}")
                    return date
        
        logger.debug(f"Could not extract date from: {url}")
        return None


# Convenience functions
def extract_date(url: str, text: str = None, headers: Dict[str, str] = None) -> Optional[datetime]:
    """Quick date extraction."""
    return DateExtractor.extract_document_date(url, text, None, headers)


def is_recent(date: Optional[datetime], years: int = 3) -> bool:
    """Check if date is recent (within years)."""
    return DateExtractor.is_within_years(date, years)


# Example usage
if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("https://example.com/reports/2024/Q4/financial.pdf", "Q4 2024 Financial Report"),
        ("https://example.com/docs/report_20240115.pdf", "Annual Report"),
        ("https://example.com/files/old_report.pdf", "December 2020 Report"),
        ("https://example.com/report.pdf", "Latest Financial Results"),
    ]
    
    for url, text in test_cases:
        date = extract_date(url, text)
        recent = is_recent(date, years=3)
        print(f"URL: {url}")
        print(f"  Date: {date}")
        print(f"  Recent: {recent}")
        print()
