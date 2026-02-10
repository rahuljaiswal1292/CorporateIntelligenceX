"""
Enhanced Download Manager for ADX/DFM Scrapers

Provides reliable file downloads with:
- Dual download strategy (click + URL fallback)
- Content validation (magic bytes, HTML detection)
- Date filtering (3-year window)
- Retry mechanism with exponential backoff
- Comprehensive error logging
"""

import os
import re
import time
import asyncio
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import Page, Download, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)


class DownloadManager:
    """
    Manages file downloads with validation, retry logic, and date filtering.
    """
    
    # File signature magic bytes
    FILE_SIGNATURES = {
        'pdf': b'%PDF',
        'xlsx': b'PK\x03\x04',  # ZIP-based format
        'xls': b'\xd0\xcf\x11\xe0',  # OLE2 format
        'docx': b'PK\x03\x04',
        'doc': b'\xd0\xcf\x11\xe0',
        'pptx': b'PK\x03\x04',
        'ppt': b'\xd0\xcf\x11\xe0',
        'csv': None,  # Text-based, no signature
    }
    
    def __init__(self, max_age_years: int = 3, min_file_size: int = 500):
        """
        Initialize download manager.
        
        Args:
            max_age_years: Maximum age of documents to download (default: 3 years)
            min_file_size: Minimum valid file size in bytes (default: 500)
        """
        self.max_age_years = max_age_years
        self.min_file_size = min_file_size
        self.download_stats = {
            'attempted': 0,
            'successful': 0,
            'failed': 0,
            'skipped_old': 0,
            'skipped_invalid': 0
        }
    
    async def download_with_retry(
        self, 
        element, 
        page: Page, 
        doc_info: Dict,
        target_dir: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """
        Download file with retry mechanism.
        
        Args:
            element: Playwright element to click
            page: Playwright page object
            doc_info: Document metadata (url, text, title, expected_type)
            target_dir: Target directory for download
            max_retries: Maximum retry attempts
            
        Returns:
            Path to downloaded file or None if failed
        """
        self.download_stats['attempted'] += 1
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries}: {doc_info.get('text', 'Unknown')[:50]}")
                
                # Add human-like delay
                await self._add_human_delay()
                
                # Attempt download with dual strategy
                result = await self._download_with_dual_strategy(element, page, doc_info, target_dir)
                
                if result:
                    logger.info(f"✓ Download successful: {os.path.basename(result)}")
                    self.download_stats['successful'] += 1
                    return result
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 1.0  # 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        logger.error(f"✗ Download failed after {max_retries} attempts: {doc_info.get('url', 'Unknown')}")
        self.download_stats['failed'] += 1
        return None
    
    async def download_batch_parallel(
        self,
        page: Page,
        documents: List[Dict],
        target_dir: str,
        max_concurrent: int = 10,
        max_retries: int = 3
    ) -> List[Optional[str]]:
        """
        Download multiple documents in parallel with concurrency control.
        
        Args:
            page: Playwright page object
            documents: List of document info dicts (url, text, title, expected_type)
            target_dir: Target directory for downloads
            max_concurrent: Maximum concurrent downloads (default: 10)
            max_retries: Maximum retry attempts per file
            
        Returns:
            List of downloaded file paths (None for failed downloads)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(doc: Dict, index: int) -> Optional[str]:
            """Download single document with semaphore control."""
            async with semaphore:
                try:
                    logger.info(f"[{index + 1}/{len(documents)}] Processing: {doc.get('text', 'Unknown')[:60]}")
                    
                    # Find element
                    url = doc['url']
                    link_selector = f'a[href="{url}"]'
                    link = page.locator(link_selector).first
                    
                    if await link.count() > 0:
                        result = await self.download_with_retry(
                            element=link,
                            page=page,
                            doc_info=doc,
                            target_dir=target_dir,
                            max_retries=max_retries
                        )
                        
                        if result:
                            logger.info(f"✓ [{index + 1}/{len(documents)}] Downloaded: {os.path.basename(result)}")
                            return result
                        else:
                            logger.warning(f"✗ [{index + 1}/{len(documents)}] Failed: {doc.get('text', 'Unknown')[:50]}")
                            return None
                    else:
                        logger.warning(f"Link element not found for: {url[:80]}")
                        return None
                        
                except Exception as e:
                    logger.error(f"Error processing document {index + 1}: {e}")
                    return None
        
        # Execute all downloads in parallel
        logger.info(f"Starting parallel download of {len(documents)} documents (max {max_concurrent} concurrent)...")
        start_time = time.time()
        
        tasks = [download_with_semaphore(doc, i) for i, doc in enumerate(documents)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to None
        results = [r if not isinstance(r, Exception) else None for r in results]
        
        elapsed = time.time() - start_time
        successful = sum(1 for r in results if r is not None)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Parallel Download Complete:")
        logger.info(f"  Total: {len(documents)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {len(documents) - successful}")
        per_file_time = f"{elapsed/len(documents):.1f}s" if len(documents) > 0 else "N/A"
        logger.info(f"  Time: {elapsed:.1f}s ({per_file_time} per file)")
        logger.info(f"{'='*60}\n")
        
        return results
    
    async def _download_with_dual_strategy(
        self,
        element,
        page: Page,
        doc_info: Dict,
        target_dir: str
    ) -> Optional[str]:
        """
        Try multiple download strategies in sequence.
        
        Strategy 1: Click and wait for download event (preferred)
        Strategy 2: Extract URL and download via context.request
        Strategy 3: Execute JavaScript to trigger download
        """
        
        # Strategy 1: Click-based download
        try:
            async with page.expect_download(timeout=30000) as download_info:
                await element.click()
            
            download = await download_info.value
            
            # Get temporary path
            temp_path = await download.path()
            
            # Validate content
            if not await self._validate_file_content(temp_path, doc_info):
                logger.warning("File validation failed (Strategy 1)")
                return None
            
            # Check date
            doc_date = await self._extract_document_date(temp_path, doc_info)
            if not self._is_document_recent(doc_date):
                logger.info(f"Skipping old document: {doc_date}")
                self.download_stats['skipped_old'] += 1
                return None
            
            # Save to target directory
            filename = download.suggested_filename
            final_path = os.path.join(target_dir, filename)
            
            # Avoid overwriting
            final_path = self._get_unique_filepath(final_path)
            
            await download.save_as(final_path)
            logger.info(f"Saved via Strategy 1: {filename}")
            return final_path
            
        except PlaywrightTimeoutError:
            logger.debug("Strategy 1 (click) timed out, trying Strategy 2")
        except Exception as e:
            logger.debug(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Direct URL download
        try:
            url = await element.get_attribute('href')
            if url and url.startswith('http'):
                return await self._download_from_url(page, url, doc_info, target_dir)
        except Exception as e:
            logger.debug(f"Strategy 2 failed: {e}")
        
        # Strategy 3: JavaScript trigger
        try:
            logger.debug("Trying Strategy 3 (JavaScript trigger)")
            await element.evaluate('el => el.click()')
            await page.wait_for_timeout(5000)
            
            # Check if file appeared in target directory
            return await self._check_latest_download(target_dir)
        except Exception as e:
            logger.debug(f"Strategy 3 failed: {e}")
        
        return None
    
    async def _download_from_url(
        self,
        page: Page,
        url: str,
        doc_info: Dict,
        target_dir: str
    ) -> Optional[str]:
        """
        Download file directly from URL using page context.
        """
        try:
            logger.info(f"Downloading from URL: {url[:80]}...")
            
            # Use page context to maintain session/cookies
            response = await page.context.request.get(url)
            
            if not response.ok:
                logger.warning(f"Request failed with status {response.status}")
                return None
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                logger.warning("Response is HTML, not a file")
                self.download_stats['skipped_invalid'] += 1
                return None
            
            # Get content
            content = await response.body()
            
            # Validate content
            if not self._validate_content_bytes(content, doc_info):
                logger.warning("Content validation failed")
                self.download_stats['skipped_invalid'] += 1
                return None
            
            # Generate filename
            filename = self._generate_filename(url, doc_info, content_type)
            filepath = os.path.join(target_dir, filename)
            filepath = self._get_unique_filepath(filepath)
            
            # Write file
            with open(filepath, 'wb') as f:
                f.write(content)
            
            # Check date after download
            doc_date = await self._extract_document_date(filepath, doc_info)
            if not self._is_document_recent(doc_date):
                logger.info(f"Removing old document: {doc_date}")
                os.remove(filepath)
                self.download_stats['skipped_old'] += 1
                return None
            
            logger.info(f"Saved via Strategy 2: {filename} ({len(content):,} bytes)")
            return filepath
            
        except Exception as e:
            logger.error(f"URL download failed: {e}")
            return None
    
    def _validate_content_bytes(self, content: bytes, doc_info: Dict) -> bool:
        """Validate file content bytes."""
        
        # Check for HTML
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html') or b'<html' in content[:200]:
            logger.warning("Content is HTML")
            return False
        
        # Check minimum size
        if len(content) < self.min_file_size:
            logger.warning(f"Content too small: {len(content)} bytes")
            return False
        
        # Check magic bytes if expected type is known
        expected_type = doc_info.get('expected_type', '').lower()
        if expected_type in self.FILE_SIGNATURES:
            expected_sig = self.FILE_SIGNATURES[expected_type]
            if expected_sig and not content.startswith(expected_sig):
                logger.warning(f"Invalid signature for {expected_type}")
                return False
        
        return True
    
    async def _validate_file_content(self, filepath: str, doc_info: Dict) -> bool:
        """Validate downloaded file content."""
        
        if not os.path.exists(filepath):
            return False
        
        # Read first 1KB for validation
        try:
            with open(filepath, 'rb') as f:
                header = f.read(1024)
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return False
        
        return self._validate_content_bytes(header, doc_info)
    
    async def _extract_document_date(self, filepath: str, doc_info: Dict) -> Optional[datetime]:
        """
        Extract document date using multiple strategies.
        
        Priority:
        1. Filename patterns
        2. Link text/title
        3. PDF metadata
        4. First page text
        """
        
        # Strategy 1: Filename
        filename = os.path.basename(filepath)
        date = self._extract_date_from_text(filename)
        if date:
            logger.debug(f"Date from filename: {date}")
            return date
        
        # Strategy 2: Link text/title
        link_text = f"{doc_info.get('text', '')} {doc_info.get('title', '')}"
        date = self._extract_date_from_text(link_text)
        if date:
            logger.debug(f"Date from link text: {date}")
            return date
        
        # Strategy 3: PDF metadata (if PDF)
        if filepath.endswith('.pdf'):
            date = await self._extract_date_from_pdf_metadata(filepath)
            if date:
                logger.debug(f"Date from PDF metadata: {date}")
                return date
        
        # Strategy 4: First page text (PDF)
        if filepath.endswith('.pdf'):
            date = await self._extract_date_from_pdf_first_page(filepath)
            if date:
                logger.debug(f"Date from PDF first page: {date}")
                return date
        
        # Strategy 5: Excel metadata
        if filepath.endswith(('.xlsx', '.xls')):
            date = await self._extract_date_from_excel(filepath)
            if date:
                logger.debug(f"Date from Excel: {date}")
                return date
        
        logger.debug("Could not extract date, assuming recent")
        return datetime.now()  # Default to now if uncertain
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Extract date from text using regex patterns."""
        
        patterns = [
            # YYYY-MM-DD, YYYY_MM_DD, YYYYMMDD
            (r'(\d{4})[_-]?(\d{2})[_-]?(\d{2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
            
            # DD-MM-YYYY, DD_MM_YYYY
            (r'(\d{2})[_-](\d{2})[_-](\d{4})', lambda m: datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
            
            # Q1-2024, Q1 2024, Q12024
            (r'Q([1-4])[_\s-]?(\d{4})', lambda m: datetime(int(m.group(2)), int(m.group(1)) * 3, 1)),
            
            # FY2024, FY-2024, FY 2024
            (r'FY[_\s-]?(\d{4})', lambda m: datetime(int(m.group(1)), 12, 31)),
            
            # Month-Year: Jan-2024, January 2024
            (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[_\s-]?(\d{4})', 
             lambda m: datetime(int(m.group(2)), self._month_to_num(m.group(1)), 1)),
            
            # Year only: 2024
            (r'\b(20\d{2})\b', lambda m: datetime(int(m.group(1)), 6, 30)),
        ]
        
        for pattern, converter in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return converter(match)
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _month_to_num(self, month_str: str) -> int:
        """Convert month abbreviation to number."""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month_str.lower()[:3], 1)
    
    async def _extract_date_from_pdf_metadata(self, filepath: str) -> Optional[datetime]:
        """Extract date from PDF metadata."""
        try:
            import PyPDF2
            with open(filepath, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                if pdf.metadata:
                    # Try creation date
                    if pdf.metadata.get('/CreationDate'):
                        date_str = pdf.metadata['/CreationDate']
                        return self._parse_pdf_date(date_str)
                    # Try modification date
                    if pdf.metadata.get('/ModDate'):
                        date_str = pdf.metadata['/ModDate']
                        return self._parse_pdf_date(date_str)
        except Exception as e:
            logger.debug(f"PDF metadata extraction failed: {e}")
        
        return None
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parse PDF date format: D:YYYYMMDDHHmmSS"""
        try:
            # Remove D: prefix and timezone
            date_str = date_str.replace('D:', '').split('+')[0].split('-')[0]
            if len(date_str) >= 8:
                year = int(date_str[0:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                return datetime(year, month, day)
        except:
            pass
        return None
    
    async def _extract_date_from_pdf_first_page(self, filepath: str) -> Optional[datetime]:
        """Extract date from first page text of PDF."""
        try:
            import PyPDF2
            with open(filepath, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                if len(pdf.pages) > 0:
                    first_page = pdf.pages[0]
                    text = first_page.extract_text()
                    # Look for date in first 500 characters
                    return self._extract_date_from_text(text[:500])
        except Exception as e:
            logger.debug(f"PDF first page extraction failed: {e}")
        
        return None
    
    async def _extract_date_from_excel(self, filepath: str) -> Optional[datetime]:
        """Extract date from Excel file."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
            ws = wb.active
            
            # Check first 10 rows, 5 columns for dates
            for row in ws.iter_rows(max_row=10, max_col=5):
                for cell in row:
                    if cell.value:
                        # Check if it's a datetime object
                        if isinstance(cell.value, datetime):
                            return cell.value
                        # Try parsing as text
                        date = self._extract_date_from_text(str(cell.value))
                        if date:
                            return date
        except Exception as e:
            logger.debug(f"Excel date extraction failed: {e}")
        
        return None
    
    def _is_document_recent(self, doc_date: Optional[datetime]) -> bool:
        """Check if document is within the age threshold."""
        if doc_date is None:
            return True  # If uncertain, download it
        
        cutoff_date = datetime.now() - timedelta(days=self.max_age_years * 365)
        return doc_date >= cutoff_date
    
    def _generate_filename(self, url: str, doc_info: Dict, content_type: str) -> str:
        """Generate filename from URL or document info with improved context preservation."""
        
        # Try to get from URL
        filename = url.split('/')[-1].split('?')[0]
        
        if not filename or '.' not in filename or len(filename) < 5:
            # Generate from doc text with better preservation
            text = doc_info.get('text', 'document').strip()
            title = doc_info.get('title', '').strip()
            
            # Prefer title if available, otherwise use text
            source_text = title if title and len(title) > len(text) else text
            
            # Sanitize but preserve meaningful characters
            # Keep alphanumeric, spaces, hyphens, underscores
            safe_text = re.sub(r'[^\w\s\-_()]', '', source_text)
            # Replace multiple spaces with single underscore
            safe_text = re.sub(r'\s+', '_', safe_text)
            # Remove leading/trailing underscores
            safe_text = safe_text.strip('_')
            
            # Limit to 150 characters but try to break at word boundary
            if len(safe_text) > 150:
                safe_text = safe_text[:150]
                # Try to break at last underscore
                last_underscore = safe_text.rfind('_')
                if last_underscore > 100:  # Only if we have at least 100 chars
                    safe_text = safe_text[:last_underscore]
            
            # If still empty, use fallback
            if not safe_text or len(safe_text) < 3:
                safe_text = 'document'
            
            # Try to extract year/date from text or URL
            year_suffix = ''
            date_match = re.search(r'(20\d{2})', f"{source_text} {url}")
            if date_match:
                year_suffix = f"_{date_match.group(1)}"
            
            # Determine extension from content type or expected type
            ext = doc_info.get('expected_type', 'pdf').lower()
            
            # Override with content type if available
            if 'pdf' in content_type:
                ext = 'pdf'
            elif 'excel' in content_type or 'spreadsheet' in content_type:
                ext = 'xlsx'
            elif 'word' in content_type or 'document' in content_type:
                ext = 'docx'
            elif not ext or ext == 'pdf':
                # Default to pdf if nothing else
                ext = 'pdf'
            
            # Construct final filename
            filename = f"{safe_text}{year_suffix}.{ext}"
        
        return filename
    
    def _get_unique_filepath(self, filepath: str) -> str:
        """Get unique filepath by adding counter if file exists."""
        if not os.path.exists(filepath):
            return filepath
        
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        
        return f"{base}_{counter}{ext}"
    
    async def _check_latest_download(self, target_dir: str) -> Optional[str]:
        """Check for latest downloaded file in directory."""
        try:
            files = [os.path.join(target_dir, f) for f in os.listdir(target_dir)]
            if not files:
                return None
            
            # Get most recent file
            latest_file = max(files, key=os.path.getctime)
            
            # Check if it was created in last 10 seconds
            if time.time() - os.path.getctime(latest_file) < 10:
                return latest_file
        except:
            pass
        
        return None
    
    async def _add_human_delay(self, min_ms: int = 300, max_ms: int = 1000):
        """Add random delay to mimic human behavior."""
        import random
        delay = random.randint(min_ms, max_ms) / 1000.0
        await asyncio.sleep(delay)
    
    def get_stats(self) -> Dict:
        """Get download statistics."""
        return self.download_stats.copy()
    
    def reset_stats(self):
        """Reset download statistics."""
        self.download_stats = {
            'attempted': 0,
            'successful': 0,
            'failed': 0,
            'skipped_old': 0,
            'skipped_invalid': 0
        }
