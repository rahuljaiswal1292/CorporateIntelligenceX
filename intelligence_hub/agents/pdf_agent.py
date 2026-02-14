import os
import fitz  # PyMuPDF
import json
from typing import List, Dict, Optional, Callable
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from .base_agent import BaseAgent
from intelligence_hub.config.config import DATA_DIRECTORY


class PdfAgent(BaseAgent):
    """
    Agent 5: The PDF Processor.
    Parses PDFs, chunks text, saves to Vector DB, and extracts insights.
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
        if not self.prompts:
            self.log("No prompts loaded from pdf_prompts.json", "WARNING")

    def _load_prompts(self) -> List[Dict]:
        try:
            with open("intelligence_hub/prompts/pdf_prompts.json", "r") as f:
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
        company_name = state.get("company_name", "Unknown")
        safe_company_name = company_name.strip()
        data_dir = os.path.join(DATA_DIRECTORY, safe_company_name)

        # Check if directory exists and has PDFs
        if not os.path.exists(data_dir):
            return (False, f"Directory not found: {data_dir}")

        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]

        if not pdf_files:
            return (False, f"No PDFs found in {data_dir}")

        return (True, f"Found {len(pdf_files)} PDFs to process")

    def execute(self, state: AgentState) -> Dict:
        """
        Execute PDF processing

        Args:
            state: Shared agent state

        Returns:
            Result with PDF analysis data
        """
        company_name = state.get("company_name", "Unknown")
        safe_company_name = company_name.strip()
        data_dir = os.path.join(DATA_DIRECTORY, safe_company_name)

        self.log(f"Processing PDFs for: {company_name}")
        pdf_results = []

        # Find PDFs
        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
        self.log(f"Found {len(pdf_files)} PDFs. Processing...")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(data_dir, pdf_file)
            try:
                # 1. Parse & Chunk
                text_chunks = self.process_pdf(pdf_path)
                self.log(f"Extracted {len(text_chunks)} chunks from {pdf_file}")

                # 2. Store to ChromaDB via profile_store
                if self.profile_store:
                    # Store chunks as enrichment data
                    for i, chunk in enumerate(text_chunks):
                        chunk_data = {
                            "source": pdf_file,
                            "company": company_name,
                            "chunk_index": i,
                            "text": chunk,
                        }
                        self.profile_store.store_enrichment_data(
                            canonical_name=company_name,
                            enrichment_data=chunk_data,
                            document_type="pdf_chunk",
                        )
                    self.log(f"Stored {len(text_chunks)} chunks to ChromaDB")

                # 3. Dynamic Extraction using prompts
                extracted_info = {}
                for prompt_cfg in self.prompts:
                    # Get relevant chunks from ChromaDB
                    if self.profile_store:
                        enrichment_data = self.profile_store.get_enrichment_data(
                            canonical_name=company_name,
                            document_type="pdf_chunk",
                        )
                        pdf_chunks = enrichment_data.get("pdf_chunk", [])

                        # Filter chunks from this specific PDF
                        relevant_chunks = [
                            c.get("text", "")
                            for c in pdf_chunks
                            if c.get("source") == pdf_file
                        ][
                            :3
                        ]  # Top 3 chunks

                        context_str = "\n".join(relevant_chunks)
                    else:
                        # Fallback: use first few chunks
                        context_str = "\n".join(text_chunks[:3])

                    # LLM Extraction
                    full_prompt = f"""
                    Context from {pdf_file}:
                    {context_str}
                    
                    Task: {prompt_cfg['prompt']}
                    
                    Return a concise summary or answer.
                    """
                    response = self.llm_connector.analyze(full_prompt)
                    extracted_info[prompt_cfg["category"]] = response

                pdf_results.append({"file": pdf_file, "analysis": extracted_info})
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

    def run(self, state: AgentState) -> AgentState:
        """
        Run PDF agent workflow

        Args:
            state: Current agent state

        Returns:
            Updated agent state
        """
        logs = []

        # Check if should execute
        should_run, reasoning = self.should_execute(state)

        if not should_run:
            self.log(f"Skipping PDF processing: {reasoning}")
            logs.append(f"PdfAgent: Skipped - {reasoning}")
            return {**state, "logs": logs, "pdf_results": []}

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
