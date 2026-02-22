import os
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
        nested_dir = os.path.join(
            DATA_DIRECTORY, exchange, safe_company_name, "reports", "structured"
        )

        if os.path.exists(nested_dir):
            # Check if likely pdfs exist or if dir just exists (returning dir is safer if we want to log "no files found" later)
            return nested_dir

        return None

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """Decide if PDF processing should run"""
        data_dir = self._get_data_dir(state)

        if not data_dir:
            return (False, "No PDF directory found with files for this company.")

        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
        return (True, f"Found {len(pdf_files)} PDFs in {data_dir}")

    def execute(self, state: AgentState) -> Dict:
        """Execute Optimized PDF processing"""
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

        # Find PDFs
        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
        # Sort by name (often includes date/year) to process newest first might be better?
        # For now just standard sort
        pdf_files.sort()

        self.log(f"Found {len(pdf_files)} PDFs. Starting prioritized analysis...")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(data_dir, pdf_file)

            # 1. Duplicate Check
            file_hash = self._get_file_hash(pdf_path)
            if file_hash in self.processed_hashes:
                self.log(f"Skipping duplicate file: {pdf_file}")
                continue
            self.processed_hashes.add(file_hash)

            try:
                # 2. Smart Extraction
                analysis_result = self.analyze_pdf_smart(pdf_path, pdf_file)

                if analysis_result:
                    pdf_results.append(analysis_result)

                    # 3. Store Insights to Profile Store
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

                # C. Extract Text from Targeted Pages
                sorted_pages = sorted(list(pages_to_read))
                self.log(f"Reading {len(sorted_pages)} specific pages from {file_name}")

                for pg_num in sorted_pages:
                    relevant_text += (
                        f"--- Page {pg_num} ---\n{doc[pg_num].get_text()}\n"
                    )

            else:
                # Fallback: No targets found from TOC
                if total_pages <= 20:
                    self.log(
                        f"No TOC targets found, but doc is small ({total_pages} pgs). Reading full."
                    )
                    for page in doc:
                        relevant_text += page.get_text() + "\n"
                else:
                    self.log(
                        "No TOC targets found in large doc. Reading first 10 and last 5 pages."
                    )
                    # Read first 10
                    for i in range(
                        min(10, total_pages)
                    ):  # Ensure not to go out of bounds for very small docs
                        relevant_text += doc[i].get_text() + "\n"
                    # Read last 5 (often financials are at the end)
                    for i in range(
                        max(0, total_pages - 5), total_pages
                    ):  # Ensure not to go out of bounds
                        relevant_text += doc[i].get_text() + "\n"

        # D. LLM Extraction on Focused Text
        # Process each category prompt
        prompts = self._load_prompts()
        for prompt_cfg in prompts:
            cat = prompt_cfg.get("category")
            if cat == "toc_analysis":
                continue  # Skip the helper prompt

            prompt_text = prompt_cfg.get("prompt")
            response = ""

            if is_image_pdf:
                self.log(f"Analyzing {cat} via Vision...")
                full_prompt = f"Analyze these document images from {file_name}. Task: {prompt_text}. Return strictly valid JSON."
                response = self.llm_connector.analyze_with_images(
                    full_prompt, page_images
                )
            else:
                context_snippet = relevant_text[:25000]
                full_prompt = f"""
                Analyze the following text extracted from a corporate report ({file_name}).
                
                Text:
                {context_snippet}
                
                Task: {prompt_text}
                
                Return strictly valid JSON.
                """
                response = self.llm_connector.analyze(full_prompt)

            # Try to parse JSON
            try:
                # Clean markdown code blocks if present
                clean_resp = response.replace("```json", "").replace("```", "").strip()
                data_json = json.loads(clean_resp)
                extracted_data[cat] = data_json
            except:
                # Fallback to raw string if json fails
                extracted_data[cat] = response

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

    def run(self, state: AgentState) -> AgentState:
        """Run PDF agent workflow"""
        logs = state.get("logs", [])
        should_run, reasoning = self.should_execute(state)

        if not should_run:
            self.log(f"Skipping PDF processing: {reasoning}")
            logs.append(f"PdfAgent: Skipped - {reasoning}")
            return {"logs": logs, "pdf_results": []}

        try:
            result = self.execute(state)
            pdf_results = result.get("data", [])
            logs.append(f"PdfAgent: Processed {len(pdf_results)} PDFs (Smart Mode)")
            return {"logs": logs, "pdf_results": pdf_results}
        except Exception as e:
            self.log(f"PDF processing failed: {e}", "ERROR")
            logs.append(f"PdfAgent: Failed - {str(e)}")
            return {"logs": logs, "pdf_results": []}
