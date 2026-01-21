import os
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeConnector:
    """
    Connector for Pinecone Vector DB with Mock Mode.
    Handles upserting and querying document chunks.
    """
    def __init__(self, api_key: Optional[str] = None, env: str = "gcp-starter"):
        self.api_key = api_key or os.getenv("PINECONE_API_KEY")
        self.env = os.getenv("PINECONE_ENV", env)
        
        if self.api_key:
            try:
                from pinecone import Pinecone
                self.pc = Pinecone(api_key=self.api_key)
                self.index_name = "corporate-intelligence"
                self.mode = "LIVE"
                # Note: In real app, we'd check if index exists
            except ImportError:
                logger.error("Pinecone client not installed.")
                self.mode = "MOCK"
        else:
            self.mode = "MOCK"
            logger.warning("PINECONE_API_KEY not found. Running in MOCK MODE.")

    def search(self, query: str, top_k: int = 3) -> List[str]:
        """
        Searches the index for relevant chunks.
        """
        logger.info(f"[{self.mode}] Vector Search: '{query}'")
        
        if self.mode == "LIVE":
            # Real implementation would go here
            # index = self.pc.Index(self.index_name)
            # res = index.query(vector=..., top_k=top_k)
            return [] 
        else:
            return self._get_mock_chunks()

    def upsert(self, documents: List[str], metadata: List[Dict]):
        """
        Upserts documents into the index.
        """
        logger.info(f"[{self.mode}] Upserting {len(documents)} documents.")
        if self.mode == "LIVE":
            pass # Actual implementation omitted for brevity
        return True

    def _get_mock_chunks(self) -> List[str]:
        """Returns mock report chunks for RAG simulation."""
        return [
            "Note 14 (Sukuk): The Group has issued a US$ 750 million Sukuk maturing in September 2025. The profit rate is fixed at 4.5%...",
            "Segment Reporting: The International Business generated AED 12 billion in revenue, driven by strong export growth in the Asian market...",
            "Risk Factors: The Group is exposed to interest rate risk primarily arising from its core lending activities..."
        ]
