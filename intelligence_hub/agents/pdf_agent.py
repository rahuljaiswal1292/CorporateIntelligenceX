import os
import fitz  # PyMuPDF
import logging
import json
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.connectors.vector_db import VectorDBConnector
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PdfAgent:
    """
    Agent 5: The PDF Processor.
    Parses PDFs, chunks text, saves to Vector DB, and extracts insights.
    """

    def __init__(self):
        self.llm = LLMConnector()
        self.vector_db = VectorDBConnector()
        self.prompts = self._load_prompts()
        if not self.prompts:
            logger.warning("PdfAgent: No prompts loaded from pdf_prompts.json")

    def _load_prompts(self) -> List[Dict]:
        try:
            with open("intelligence_hub/prompts/pdf_prompts.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load PDF prompts: {e}")
            return []

    def run(self, state: AgentState) -> AgentState:
        logger.info("PdfAgent: Checking for documents...")
        logs = state.get("logs", [])
        pdf_results = []

        company_name = state.get("company_name", "Unknown")
        # Ensure directory exists: data/{Company_Name}
        # Handle potential directory issues with sanitization if needed
        safe_company_name = company_name.strip()
        data_dir = os.path.join("intelligence_hub", "data", safe_company_name)

        if not os.path.exists(data_dir):
            logs.append(f"PdfAgent: Directory not found: {data_dir}")
            return {**state, "logs": logs, "pdf_results": []}

        # Find PDFs
        pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]

        if not pdf_files:
            logs.append(f"PdfAgent: No PDFs found in {data_dir}")
            return {**state, "logs": logs, "pdf_results": []}

        logs.append(f"PdfAgent: Found {len(pdf_files)} PDFs. Processing...")

        for pdf_file in pdf_files:
            pdf_path = os.path.join(data_dir, pdf_file)
            try:
                # 1. Parse & Chunk
                text_chunks = self.process_pdf(pdf_path)

                # 2. Upsert to Vector DB
                # Metadata including filename and company
                metadata = [
                    {"source": pdf_file, "company": company_name} for _ in text_chunks
                ]
                self.vector_db.upsert_documents(text_chunks, metadata)
                logs.append(f"PdfAgent: Processed & Indexed {pdf_file}")

                # 3. Dynamic Extraction
                extracted_info = {}
                for prompt_cfg in self.prompts:
                    # RAG Retrieval for specific prompt
                    context = self.vector_db.search(
                        prompt_cfg["prompt"],
                        top_k=3,
                        filter_conditions={"source": pdf_file},
                    )
                    context_str = "\n".join(context)

                    # LLM Extraction
                    full_prompt = f"""
                    Context from {pdf_file}:
                    {context_str}
                    
                    Task: {prompt_cfg['prompt']}
                    
                    Return a concise summary or answer.
                    """
                    response = self.llm.analyze(full_prompt)
                    extracted_info[prompt_cfg["category"]] = response

                pdf_results.append({"file": pdf_file, "analysis": extracted_info})

            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                logs.append(f"PdfAgent: Error processing {pdf_file}")

        return {**state, "logs": logs, "pdf_results": pdf_results}

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
