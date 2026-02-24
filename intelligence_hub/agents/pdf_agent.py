import os
import re
import fitz  # PyMuPDF
import json
import hashlib
import base64
from typing import List, Dict, Optional, Callable, Set
from intelligence_hub.graph.state import AgentState
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from .base_agent import BaseAgent
from intelligence_hub.config.config import DATA_DIRECTORY


class PdfAgent(BaseAgent):
    """
    Agent 5: The PDF Processor.
    Optimized for efficiency:
    1. Skips duplicates via hashing.
    2. Identifies relevant pages via TOC scan (Smart Index-Aware).
    3. Extracts targeted insights (Financials, Structure) via LLM.
    """

    def _clean_text(self, text: str) -> str:
        """Collapse multiple spaces and newlines to reduce token count."""
        if not text:
            return ""
        # Collapse multiple spaces
        text = re.sub(r" +", " ", text)
        # Collapse multiple newlines
        text = re.sub(r"\n+", "\n", text)
        return text.strip()

    """
    Agent 5: The PDF Processor.
    Optimized for efficiency:
    1. Skips duplicates via hashing.
    2. Identifies relevant pages via TOC scan (Smart Index-Aware).
    3. Extracts targeted insights (Financials, Structure) via LLM.
    """

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="PDF Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )
        self.prompts = self._load_prompts()
        self.processed_hashes: Set[str] = set()
        if not self.prompts:
            self.log("No prompts loaded from pdf_prompts.json", "WARNING")

    def _load_prompts(self) -> List[Dict]:
        try:
            prompt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "prompts",
                "pdf_prompts.json",
            )
            with open(prompt_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.log(f"Failed to load PDF prompts: {e}", "ERROR")
            return []

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Decide if PDF processing should run

        Args:
            state: Shared agent state

        Returns:
            (should_run, reasoning)
        """
        company_name = state.get("company_name") or "Unknown"
        safe_company_name = str(company_name).strip()

        # Try multiple directory variants for robustness
        potential_paths = [
            os.path.join(DATA_DIRECTORY, safe_company_name),  # Exact match
            os.path.join(
                DATA_DIRECTORY, safe_company_name.lower()
            ),  # lowercase (emaar)
            os.path.join(
                DATA_DIRECTORY, safe_company_name.title()
            ),  # title case (Emaar)
        ]

        data_dir = None
        for path in potential_paths:
            if os.path.exists(path) and os.path.isdir(path):
                data_dir = path
                break

        # Check if directory exists and has PDFs
        if not data_dir:
            return (
                False,
                f"Directory not found for {safe_company_name} (checked: {', '.join(potential_paths)})",
            )

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of the first 64KB of the file for duplicate detection."""
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                buf = f.read(65536)
                hasher.update(buf)
            return hasher.hexdigest()
        except Exception:
            return ""

    def _get_data_dir(self, state: AgentState) -> Optional[str]:
        """
        Resolve the data directory, strictly using the nested structure:
        data/Exchange/Company/reports/structured
        """
        company_name = state.get("ticker", "Unknown")
        exchange = state.get("exchange", "Unknown")
        safe_company_name = company_name.strip()

        # Nested Structure (data/Exchange/Company/reports/structured)

        if exchange == "DFM":
            nested_dir = os.path.join(
                DATA_DIRECTORY, exchange, safe_company_name, "reports", "structured"
            )
        else:
            nested_dir = os.path.join(
                DATA_DIRECTORY, exchange, safe_company_name, "financials", "structured"
            )

        if os.path.exists(nested_dir):
            # Check if likely pdfs exist or if dir just exists (returning dir is safer if we want to log "no files found" later)
            return nested_dir

        return None

    def _get_report_year(self, pdf_path: str, file_name: str) -> Optional[int]:
        """
        Extract the report year deterministically without LLM.
        Priority:
        1. 4-digit year in filename (2020-2029)
        2. Year in PDF metadata
        3. Regex search for year in first 2 pages
        """
        # 1. Filename Year (Regex for 202[0-9])
        # Using a more flexible regex that doesn't rely strictly on \b (which fails with underscores)
        year_match = re.search(r"(?:^|[^0-9])(202[0-9])(?:[^0-9]|$)", file_name)
        if year_match:
            return int(year_match.group(1))

        try:
            doc = fitz.open(pdf_path)

            # 2. Metadata Check
            metadata = doc.metadata or {}
            creation_date = metadata.get("creationDate", "")
            if (
                creation_date
                and len(creation_date) > 5
                and creation_date.startswith("D:")
            ):
                # Format is usually D:YYYYMMDD...
                meta_year_str = creation_date[2:6]
                if meta_year_str.isdigit():
                    return int(meta_year_str)

            # 3. First 2 pages regex
            for i in range(min(2, len(doc))):
                text = doc[i].get_text().strip()
                # Look for "202x" surrounded by word boundaries or specific labels
                # e.g. "Annual Report 2025", "FY 2026"
                page_year_match = re.search(r"\b(202[4-9])\b", text)
                if page_year_match:
                    doc.close()
                    return int(page_year_match.group(1))

            doc.close()
        except Exception:
            pass

    def _is_annual_report(self, pdf_path: str, file_name: str) -> bool:
        """
        Deterministically check if a report is likely an Annual Report.
        """
        # 1. Filename Check
        if "annual" in file_name.lower():
            return True

        # 2. Content Check (First 5 pages)
        try:
            doc = fitz.open(pdf_path)
            # Scan first 5 pages for keywords
            for i in range(min(5, len(doc))):
                text = doc[i].get_text().lower()
                if "annual report" in text or "year ended" in text:
                    doc.close()
                    return True
            doc.close()
        except:
            pass

        return False

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """Decide if PDF processing should run"""
        data_dir = self._get_data_dir(state)

        if not data_dir:
            return (False, "No PDF directory found with files for this company.")

        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
        return (True, f"Found {len(pdf_files)} PDFs in {data_dir}")

    def execute(self, state: AgentState) -> Dict:
        """Execute Optimized PDF processing - now selecting only the single latest annual report."""
        company_name = state.get("ticker", "Unknown")

        data_dir = self._get_data_dir(state)
        if not data_dir:
            self.log(f"No data directory found for {company_name}", "WARNING")
            return {
                "data": [],
                "document_type": "pdf_analysis",
                "metadata": {"pdf_count": 0},
            }

        self.log(f"Processing PDFs for: {company_name} in {data_dir}")
        pdf_results = []

        # 1. Identify all PDFs and collect metadata
        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]

        if not pdf_files:
            return {
                "data": [],
                "document_type": "pdf_analysis",
                "metadata": {"pdf_count": 0},
            }

        file_metas = []
        for f in pdf_files:
            path = os.path.join(data_dir, f)
            year = self._get_report_year(path, f) or 0
            is_annual = self._is_annual_report(path, f)
            mtime = os.path.getmtime(path)
            file_metas.append(
                {
                    "file": f,
                    "path": path,
                    "year": year,
                    "is_annual": is_annual,
                    "mtime": mtime,
                }
            )

        # 2. Selection Strategy: Prioritize Year > Is Annual > MTime
        # User requested: Only process latest ANNUAL
        sorted_metas = sorted(
            file_metas,
            key=lambda x: (x["year"], x["is_annual"], x["mtime"]),
            reverse=True,
        )

        if not sorted_metas:
            return {
                "data": [],
                "document_type": "pdf_analysis",
                "metadata": {"pdf_count": 0},
            }

        # Select target file
        best_candidate = sorted_metas[0]

        # Log skipped files
        for meta in sorted_metas[1:]:
            self.log(
                f"Skipping PDF (Not latest/annual): {meta['file']} (Year: {meta['year']}, Annual: {meta['is_annual']})"
            )

        # 3. Process the single Best Candidate
        pdf_file = best_candidate["file"]
        pdf_path = best_candidate["path"]

        # Content-based hash check
        file_hash = self._get_file_hash(pdf_path)
        if not file_hash:
            return {
                "data": [],
                "document_type": "pdf_analysis",
                "metadata": {"pdf_count": 1},
            }

        # Check existing hashes
        existing_hashes = set()
        if self.profile_store:
            try:
                existing_data = self.profile_store.get_enrichment_data(
                    company_name, "pdf_insights"
                )
                for insights in existing_data.get("pdf_insights", []):
                    h = insights.get("meta", {}).get("file_hash") or insights.get(
                        "file_hash"
                    )
                    if h:
                        existing_hashes.add(h)

                if file_hash in existing_hashes:
                    self.log(
                        f"Already processed this specific PDF: {pdf_file}. Returning cached data."
                    )
            except:
                pass

        try:
            self.log(
                f"Analyzing Target PDF: {pdf_file} (Year: {best_candidate['year']}, Annual: {best_candidate['is_annual']})"
            )
            analysis_result = self.analyze_pdf_smart(pdf_path, pdf_file)

            if analysis_result:
                if isinstance(analysis_result, dict):
                    if "meta" not in analysis_result:
                        analysis_result["meta"] = {}
                    analysis_result["meta"]["file_hash"] = file_hash
                    # Explicitly tag as annual if we determined it
                    if best_candidate["is_annual"] and not analysis_result["meta"].get(
                        "period"
                    ):
                        analysis_result["meta"][
                            "period"
                        ] = f"Annual {best_candidate['year']}"

                pdf_results.append(analysis_result)

                # Store to Profile Store
                if self.profile_store:
                    self.profile_store.store_enrichment_data(
                        canonical_name=company_name,
                        enrichment_data=analysis_result,
                        document_type="pdf_insights",
                    )
                self.log(f"Completed analysis of {pdf_file}")

        except Exception as e:
            self.log(f"Error processing {pdf_file}: {e}", "ERROR")

        return {
            "data": pdf_results,
            "document_type": "pdf_analysis",
            "metadata": {
                "pdf_count": len(pdf_files),
                "processed_count": len(pdf_results),
                "target_file": pdf_file,
            },
        }

    def analyze_pdf_smart(self, pdf_path: str, file_name: str) -> Dict:
        """
        Smart Analysis:
        1. If small file (<10 pages), read all (Text first, then Vision fallback).
        2. Else, Read TOC to find target pages.
        3. Extract text from target pages.
        4. Use LLM to extract JSON data.
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        extracted_data = {
            "source": file_name,
            "meta": {},
            "financials": {},
            "structure": {},
        }

        relevant_text = ""
        is_image_pdf = False
        page_images = []

        # Strategy A: Small Document -> Read All
        if total_pages <= 10:
            self.log(f"Small document ({total_pages} pages). Reading full text.")
            for page in doc:
                text = page.get_text()
                if text.strip():
                    relevant_text += text + "\n"

            # Fallback to Vision if text is empty
            if not relevant_text.strip():
                is_image_pdf = True
                self.log(
                    f"No text extracted from {file_name}. Attempting Vision Analysis."
                )
                for page in doc:
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("jpeg")
                    base64_img = base64.b64encode(img_data).decode("utf-8")
                    page_images.append(base64_img)

        # Strategy B: Large Document -> Smart TOC Scan
        else:
            # A. TOC Scan (First 10 pages)
            toc_limit = min(10, total_pages)
            toc_text = ""
            for i in range(toc_limit):
                toc_text += doc[i].get_text() + "\n"

            # Identify Targets via LLM
            targets = self._find_relevant_pages(toc_text)
            self.log(f"Identified targets for {file_name}: {targets}")

            # Use targets if found, else fallback
            if targets:
                # B. Define Page Sets to Read
                pages_to_read = set()

                # Always read first 3 pages for Meta/Intro
                for i in range(min(3, total_pages)):
                    pages_to_read.add(i)

                # Add Financials Pages
                fin_page = targets.get("financials_page")
                if (
                    fin_page
                    and isinstance(fin_page, int)
                    and 0 <= fin_page < total_pages
                ):
                    # Read target + next 4 pages (buffer)
                    for i in range(fin_page, min(fin_page + 5, total_pages)):
                        pages_to_read.add(i)

                # Add Structure/Subsidiaries Pages
                struct_page = targets.get("structure_page")
                if (
                    struct_page
                    and isinstance(struct_page, int)
                    and 0 <= struct_page < total_pages
                ):
                    # Read target + next 2 pages
                    for i in range(struct_page, min(struct_page + 3, total_pages)):
                        pages_to_read.add(i)

                # C. Extract Text & Images (Hybrid) from Targeted Pages
                sorted_pages = sorted(list(pages_to_read))
                self.log(f"Reading {len(sorted_pages)} specific pages from {file_name}")

                for pg_num in sorted_pages:
                    page = doc[pg_num]
                    text = page.get_text()
                    relevant_text += f"--- Page {pg_num} ---\n{text}\n"

                    # Hybrid Detection: If page has very little text, capture as image
                    if len(text.strip()) < 200:
                        self.log(
                            f"Page {pg_num} appears image-based (text len: {len(text.strip())}). Capturing image."
                        )
                        pix = page.get_pixmap()
                        img_data = pix.tobytes("jpeg")
                        base64_img = base64.b64encode(img_data).decode("utf-8")
                        page_images.append(base64_img)

            else:
                # Fallback: No targets found from TOC
                if total_pages <= 20:
                    self.log(
                        f"No TOC targets found, but doc is small ({total_pages} pgs). Reading full."
                    )
                    for page in doc:
                        text = page.get_text()
                        relevant_text += text + "\n"
                        # Also check for images in full read fallback
                        if not text.strip():
                            pix = page.get_pixmap()
                            img_data = pix.tobytes("jpeg")
                            page_images.append(
                                base64.b64encode(img_data).decode("utf-8")
                            )
                else:
                    self.log(
                        "No TOC targets found in large doc. Reading first 10 and last 5 pages."
                    )
                    # Read first 10
                    for i in range(min(10, total_pages)):
                        text = doc[i].get_text()
                        relevant_text += text + "\n"
                        if not text.strip():
                            pix = doc[i].get_pixmap()
                            img_data = pix.tobytes("jpeg")
                            page_images.append(
                                base64.b64encode(img_data).decode("utf-8")
                            )
                    # Read last 5
                    for i in range(max(0, total_pages - 5), total_pages):
                        text = doc[i].get_text()
                        relevant_text += text + "\n"
                        if not text.strip():
                            pix = doc[i].get_pixmap()
                            img_data = pix.tobytes("jpeg")
                            page_images.append(
                                base64.b64encode(img_data).decode("utf-8")
                            )

        # D. LLM Extraction on Focused Text/Images
        # Clean text to reduce token count
        clean_context = self._clean_text(relevant_text)[:30000]

        prompts = self._load_prompts()
        extraction_tasks = []
        for p in prompts:
            cat = p.get("category")
            if cat != "toc_analysis":
                extraction_tasks.append(f"- {cat.upper()}: {p.get('prompt')}")

        combined_tasks_str = "\n".join(extraction_tasks)

        # Decide between Text only or Hybrid/Vision analysis
        if page_images:
            self.log(f"Analyzing {file_name} via Hybrid Vision+Text (Consolidated)...")
            full_prompt = f"""
            Analyze these document images and text from {file_name}.
            
            EXTRACTED TEXT CONTEXT:
            {clean_context}
            
            TASKS:
            {combined_tasks_str}
            
            Return strictly valid JSON where keys are the task categories (meta, financials, structure).
            """
            response = self.llm_connector.analyze_with_images(full_prompt, page_images)
        else:
            self.log(f"Analyzing {file_name} via Text-only (Consolidated)...")
            full_prompt = f"""
            Analyze the following text extracted from a corporate report ({file_name}).
            
            TEXT:
            {clean_context}
            
            TASKS:
            {combined_tasks_str}
            
            Return strictly valid JSON where keys are the task categories (meta, financials, structure).
            """
            response = self.llm_connector.analyze(full_prompt)

        # Parse Consolidated JSON result
        try:
            # Clean markdown code blocks if present
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            data_json = json.loads(clean_resp)

            # Map back to extracted_data
            for key, val in data_json.items():
                k_lower = key.lower()
                if k_lower in extracted_data:
                    extracted_data[k_lower] = val
                else:
                    # In case LLM used a slightly different key but it's one of our categories
                    for cat in ["meta", "financials", "structure"]:
                        if cat in k_lower:
                            extracted_data[cat] = val
        except Exception as e:
            self.log(f"Failed to parse consolidated JSON: {e}.", "WARNING")
            # Fallback to per-category extraction if consolidated fails (Safety)
            self.log("Falling back to legacy per-category extraction.")
            for prompt_cfg in prompts:
                cat = prompt_cfg.get("category")
                if cat == "toc_analysis":
                    continue

                single_prompt = f"Text:\n{clean_context}\n\nTask: {prompt_cfg.get('prompt')}\nReturn JSON."
                try:
                    single_resp = self.llm_connector.analyze(single_prompt)
                    clean_s = (
                        single_resp.replace("```json", "").replace("```", "").strip()
                    )
                    extracted_data[cat] = json.loads(clean_s)
                except:
                    extracted_data[cat] = single_resp

        return extracted_data

    def _find_relevant_pages(self, toc_text: str) -> Dict[str, int]:
        """Ask LLM to find page numbers from TOC text."""
        toc_prompt_cfg = next(
            (p for p in self.prompts if p["category"] == "toc_analysis"), None
        )
        if not toc_prompt_cfg:
            return {}

        prompt = f"""
        {toc_prompt_cfg['prompt']}
        
        TOC Text:
        {toc_text[:5000]}
        """

        response = self.llm_connector.analyze(prompt)
        try:
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_resp)
        except:
            return {}

    def run(self, state: AgentState):
        """Run PDF agent workflow"""
        logs = state.get("logs", [])
        should_run, reasoning = self.should_execute(state)

        if not should_run:
            self.log(f"Skipping PDF processing: {reasoning}")
            logs.append(f"PdfAgent: Skipped - {reasoning}")
            return {"logs": logs, "pdf_results": []}

        # Execute PDF processing
        try:
            result = self.execute(state)
            pdf_results = result.get("data", [])

            logs.append(f"PdfAgent: Processed {len(pdf_results)} PDFs")
            return {**state, "logs": logs, "pdf_results": pdf_results}

        except Exception as e:
            self.log(f"PDF processing failed: {e}", "ERROR")
            logs.append(f"PdfAgent: Failed - {str(e)}")
            return {**state, "logs": logs, "pdf_results": []}

    def process_pdf(self, file_path: str) -> List[str]:
        """
        Parses PDF and returns a list of text chunks.
        """
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()

        return self.chunk_text(text)

    def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 100
    ) -> List[str]:
        """
        Simple overlapping chunker.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks
