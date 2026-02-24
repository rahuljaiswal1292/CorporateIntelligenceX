"""
Enhanced Download Manager for DFM Scraper

Provides reliable file downloads for DFM with:
- Dual download strategy (click + URL fallback)
- Content validation (magic bytes, HTML detection)
- Date filtering (3-year window)
- Retry mechanism with exponential backoff
- Specific handling for DFM session-protected links
- Metadata extraction specialized for DFM document naming conventions
"""

import os
import re
import time
import asyncio
import logging
import hashlib
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import unquote
from playwright.async_api import Page, Download, TimeoutError as PlaywrightTimeoutError

# Project imports
from intelligence_hub.config.settings import config

logger = logging.getLogger("DFMDownloadManager")

class DFMDownloadManager:
    """
    Manages file downloads for DFM with validation, retry logic, and date filtering.
    Tailored specifically for DFM's infrastructure and document structures.
    """

    # File signature magic bytes
    FILE_SIGNATURES = {
        "pdf": b"%PDF",
        "xlsx": b"PK\x03\x04",  # ZIP-based format
        "xls": b"\xd0\xcf\x11\xe0",  # OLE2 format
        "docx": b"PK\x03\x04",
        "doc": b"\xd0\xcf\x11\xe0",
        "pptx": b"PK\x03\x04",
        "ppt": b"\xd0\xcf\x11\xe0",
        "csv": None,  # Text-based, no signature
    }

    def __init__(self, max_age_years: int = 3, min_file_size: int = 500):
        """
        Initialize DFM download manager.
        """
        self.max_age_years = max_age_years
        self.min_file_size = min_file_size
        self.downloaded_hashes = {}  # hash -> filepath mapping for deduplication
        self.download_stats = {
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "skipped_old": 0,
            "skipped_invalid": 0,
            "skipped_duplicate": 0,
        }
        self.active_writes = set()
        self.file_lock = asyncio.Lock()

        # Shared URL registries — set externally by DFMScraper for cross-system dedup
        self.global_attempted_urls = None  # Reference to DFMScraper.attempted_urls
        self.global_completed_urls = None  # Reference to DFMScraper.completed_urls

    async def download_with_retry(
        self, element, page: Page, doc_info: Dict, target_dir: str, max_retries: int = 3
    ) -> Optional[str]:
        """
        Download file with retry mechanism.
        """
        self.download_stats["attempted"] += 1

        for attempt in range(max_retries):
            try:
                # Add human-like delay between attempts
                if attempt > 0:
                    await asyncio.sleep(2 * attempt)

                logger.info(
                    f"DFM Download attempt {attempt + 1}/{max_retries}: {doc_info.get('text', 'Unknown')[:50]}"
                )

                # Attempt download with dual strategy
                result = await self._download_with_dual_strategy(
                    element, page, doc_info, target_dir
                )

                if result:
                    logger.info(
                        f"✓ DFM Download successful: {os.path.basename(result)}"
                    )
                    self.download_stats["successful"] += 1
                    return result

            except Exception as e:
                logger.warning(f"DFM attempt {attempt + 1} failed: {e}")

        logger.error(
            f"✗ DFM Download failed after {max_retries} attempts: {doc_info.get('url', 'Unknown')}"
        )
        self.download_stats["failed"] += 1
        return None

    async def _download_with_dual_strategy(
        self, element, page: Page, doc_info: Dict, target_dir: str
    ) -> Optional[str]:
        """
        Try multiple download strategies for DFM.
        """
        # ── Cross-system dedup: skip if already attempted by popup handler or another tab ──
        url = doc_info.get("url", "")
        if url:
            normalized = unquote(url).split("?")[0].lower().strip()
            if self.global_attempted_urls is not None:
                if normalized in self.global_attempted_urls:
                    logger.debug(
                        f"URL already handled globally, skipping: ...{normalized[-60:]}"
                    )
                    return None
                self.global_attempted_urls.add(normalized)

        # Strategy 1: URL Based (Using browser context to maintain session)
        if not url and element:
            url = await element.get_attribute("href")

        if url and (
            url.startswith("http") or url.startswith("/") or "feeds.dfm.ae" in url
        ):
            # Resolve relative URLs
            if url.startswith("/"):
                from urllib.parse import urljoin

                url = urljoin("https://www.dfm.ae", url)

            result = await self._download_from_url(page, url, doc_info, target_dir)
            if result:
                # Mark as completed in global registry
                if self.global_completed_urls is not None:
                    normalized = unquote(url).split("?")[0].lower().strip()
                    self.global_completed_urls.add(normalized)
                return result

        # Strategy 2: Click Based (Wait for download event)
        if element:
            try:
                async with page.expect_download(timeout=15000) as download_info:
                    await element.click(force=True, timeout=5000)
                download = await download_info.value

                # Process the download
                suggested_filename = unquote(download.suggested_filename)
                # DFM often gives generic names or percent-encoded ones
                suggested_filename = re.sub(
                    r"[%\s_\-]+", " ", suggested_filename
                ).strip()
                if not suggested_filename or len(suggested_filename) < 5:
                    suggested_filename = self._generate_filename(
                        unquote(download.url), doc_info, ""
                    )

                if not suggested_filename.lower().endswith(
                    (".pdf", ".xlsx", ".xls", ".docx", ".doc")
                ):
                    # Check expected type
                    ext = doc_info.get("expected_type", "pdf")
                    suggested_filename += f".{ext}"

                filepath = os.path.join(target_dir, suggested_filename)
                filepath = self._get_unique_filepath(filepath)

                await download.save_as(filepath)

                # Validation & Dedup
                if await self._validate_file_content(filepath, doc_info):
                    # Convert HTML-XLS to real XLSX if needed
                    filepath = await self._ensure_valid_excel(filepath)

                    # Check date
                    doc_date = await self._extract_document_date(filepath, doc_info)
                    if self._is_document_recent(doc_date):
                        deduped = self._check_and_handle_duplicate(filepath, target_dir)
                        return deduped
                    else:
                        logger.info(f"DFM: Removing old doc: {doc_date}")
                        try:
                            os.remove(filepath)
                        except:
                            pass
                        self.download_stats["skipped_old"] += 1
                else:
                    logger.warning("DFM: Downloaded content invalid")
                    os.remove(filepath)
                    self.download_stats["skipped_invalid"] += 1
            except Exception as e:
                logger.debug(f"DFM Strategy 2 failed: {e}")

        return None

    async def _download_from_url(
        self, page: Page, url: str, doc_info: Dict, target_dir: str
    ) -> Optional[str]:
        """DFM Specific direct download logic."""
        try:
            # Use browser context to maintain auth cookies for DFM
            response = await page.context.request.get(url, timeout=45000)
            if response.status != 200:
                return None

            content_type = response.headers.get("content-type", "").lower()
            if "text/html" in content_type:
                return None

            content = await response.body()
            if not self._validate_content_bytes(content, doc_info):
                return None

            # Determine filename
            cd = response.headers.get("content-disposition", "")
            filename = ""
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].strip(' ";')
            if not filename:
                filename = url.split("?")[0].split("/")[-1]

            filename = unquote(filename)
            filename = re.sub(r"[%\s_\-]+", " ", filename).strip()
            if not filename or len(filename) < 5:
                filename = self._generate_filename(url, doc_info, content_type)

            if not any(
                filename.lower().endswith(ext)
                for ext in [".pdf", ".xlsx", ".xls", ".doc", ".docx"]
            ):
                ext = doc_info.get("expected_type", "pdf")
                if "." not in filename:
                    filename += f".{ext}"

            filepath = os.path.join(target_dir, filename)
            filepath = self._get_unique_filepath(filepath)

            async with self.file_lock:
                with open(filepath, "wb") as f:
                    f.write(content)

            # Convert HTML-XLS to real XLSX if needed
            filepath = await self._ensure_valid_excel(filepath)

            # Date check
            doc_date = await self._extract_document_date(filepath, doc_info)
            if self._is_document_recent(doc_date):
                return self._check_and_handle_duplicate(filepath, target_dir)
            else:
                try:
                    os.remove(filepath)
                except:
                    pass
                self.download_stats["skipped_old"] += 1
                return None

        except Exception as e:
            logger.debug(f"DFM URL download failed: {e}")
            return None

    def _validate_content_bytes(self, content: bytes, doc_info: Dict) -> bool:
        if len(content) < self.min_file_size:
            return False
        if (
            b"<html" in content[:500].lower()
            or b"<!doctype html" in content[:500].lower()
        ):
            # Exception for DFM Excel-HTML files
            if b"urn:schemas-microsoft-com:office:excel" in content[:1000].lower():
                return True
            return False
        return True

    async def _validate_file_content(self, filepath: str, doc_info: Dict) -> bool:
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, "rb") as f:
                header = f.read(1024)
            return self._validate_content_bytes(header, doc_info)
        except:
            return False

    async def _ensure_valid_excel(self, filepath: str) -> str:
        """
        Check if an .xls file is actually HTML content and convert it to real .xlsx if needed.
        Returns the new filepath (which might be .xlsx) or the original if no change.
        """
        if not filepath.lower().endswith((".xls", ".xlsx")):
            return filepath

        try:
            with open(filepath, "rb") as f:
                content_start = f.read(1024)

            # Check for Excel HTML signature
            if (
                b"<html" in content_start.lower()
                and b"urn:schemas-microsoft-com:office:excel" in content_start.lower()
            ):
                logger.info(
                    f"detected HTML content in Excel file {os.path.basename(filepath)}. Converting to XLSX..."
                )

                try:
                    import pandas as pd

                    # Use pandas to read the HTML table
                    dfs = pd.read_html(filepath)
                    if dfs:
                        df = dfs[0]  # Assume first table is the data

                        # Create new path with .xlsx extension
                        directory = os.path.dirname(filepath)
                        filename = os.path.splitext(os.path.basename(filepath))[0]
                        new_path = os.path.join(directory, f"{filename}.xlsx")
                        new_path = self._get_unique_filepath(new_path)

                        # Save as real Excel
                        df.to_excel(new_path, index=False)
                        logger.info(
                            f"Converted to real Excel: {os.path.basename(new_path)}"
                        )

                        # Remove original HTML-XLS file
                        try:
                            os.remove(filepath)
                        except:
                            pass

                        return new_path
                except Exception as e:
                    logger.warning(
                        f"Failed to convert HTML-XLS to XLSX: {e}. Keeping original."
                    )
                    return filepath

        except Exception as e:
            logger.debug(f"Error checking excel file content: {e}")

        return filepath

    async def _extract_document_date(
        self, filepath: str, doc_info: Dict
    ) -> Optional[datetime]:
        # Implementation similar to main download manager but can be tuned for DFM
        filename = os.path.basename(filepath)
        text_context = (
            f"{doc_info.get('text', '')} {doc_info.get('title', '')} {filename}"
        )

        # DFM Specific patterns (often DD MM YYYY)
        dfm_pattern = re.search(
            r"(\d{2})[\s\-_\.](\d{2})[\s\-_\.](\d{4})", text_context
        )
        if dfm_pattern:
            try:
                return datetime(
                    int(dfm_pattern.group(3)),
                    int(dfm_pattern.group(2)),
                    int(dfm_pattern.group(1)),
                )
            except:
                pass

        # Fallback to general patterns
        return self._extract_date_from_text(text_context)

    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        patterns = [
            (
                r"(\d{4})[_-]?(\d{2})[_-]?(\d{2})",
                lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))),
            ),
            (
                r"(\d{2})[_-](\d{2})[_-](\d{4})",
                lambda m: datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))),
            ),
            (r"\b(20\d{2})\b", lambda m: datetime(int(m.group(1)), 6, 30)),
        ]
        for pattern, converter in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return converter(match)
                except:
                    continue
        return None

    def _is_document_recent(self, doc_date: Optional[datetime]) -> bool:
        if doc_date is None:
            return True
        cutoff = datetime.now() - timedelta(days=self.max_age_years * 365)
        return doc_date >= cutoff

    def _generate_filename(self, url: str, doc_info: Dict, content_type: str) -> str:
        text = doc_info.get("text", "document").strip()
        safe_text = re.sub(r"[^\w\s\-]", "_", text)
        safe_text = re.sub(r"\s+", "_", safe_text).strip("_")
        ext = "pdf"
        if "excel" in content_type:
            ext = "xlsx"
        return f"{safe_text[:100]}_{int(time.time())}.{ext}"

    def _get_unique_filepath(self, filepath: str) -> str:
        if not os.path.exists(filepath):
            return filepath
        base, ext = os.path.splitext(filepath)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def _calculate_file_hash(self, filepath: str) -> str:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _check_and_handle_duplicate(
        self, filepath: str, target_dir: str
    ) -> Optional[str]:
        file_hash = self._calculate_file_hash(filepath)
        if file_hash in self.downloaded_hashes:
            existing = self.downloaded_hashes[file_hash]
            return self._resolve_duplicate(filepath, existing, file_hash)

        self.downloaded_hashes[file_hash] = filepath
        return filepath

    def _resolve_duplicate(
        self, new_file: str, existing_file: str, file_hash: str
    ) -> str:
        if os.path.abspath(new_file) == os.path.abspath(existing_file):
            return new_file
        # Prefer descriptive names
        if len(os.path.basename(new_file)) > len(os.path.basename(existing_file)):
            try:
                os.remove(existing_file)
            except:
                pass
            self.downloaded_hashes[file_hash] = new_file
            return new_file
        else:
            try:
                os.remove(new_file)
            except:
                pass
            self.download_stats["skipped_duplicate"] += 1
            return existing_file

    def get_stats(self) -> Dict:
        return self.download_stats.copy()

    async def download_batch_parallel(
        self,
        page: Page,
        documents: List[Dict],
        target_dir: str,
        max_concurrent: int = 5,
    ) -> List[Optional[str]]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def sem_download(doc, idx):
            async with semaphore:
                # Resolve link element if possible, otherwise pass None for direct URL download
                url = doc.get("url")
                link = page.locator(f'a[href="{url}"]').first if url else None
                return await self.download_with_retry(
                    link if link and await link.count() > 0 else None,
                    page,
                    doc,
                    target_dir,
                )

        tasks = [sem_download(doc, i) for i, doc in enumerate(documents)]
        return await asyncio.gather(*tasks)
