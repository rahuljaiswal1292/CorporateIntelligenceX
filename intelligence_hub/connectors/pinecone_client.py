import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from intelligence_hub.config.settings import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeConnector:
    """
    Connector for Pinecone Vector DB with Mock Mode & Staleness Checks.
    """
    def __init__(self):
        self.api_key = config.PINECONE_API_KEY
        self.env = config.PINECONE_ENV
        self.index_name = config.PINECONE_INDEX_NAME
        
        if self.api_key:
            try:
                from pinecone import Pinecone
                self.pc = Pinecone(api_key=self.api_key)
                self.index = self.pc.Index(self.index_name)
                self.mode = "LIVE"
            except Exception as e:
                logger.error(f"Pinecone Connection Failed: {e}")
                self.mode = "MOCK"
        else:
            self.mode = "MOCK"

    def check_staleness(self, ticker: str) -> bool:
        """
        Checks if data for ticker is stale (older than CACHE_TTL_HOURS).
        Returns True if stale or missing (needs scraping).
        """
        if self.mode == "MOCK":
            return True # Always scrape/simulate in Mock mode (or False if we want to test cache)

        try:
            # Query for latest 'financials' metadata
            # We assume ID format: "{ticker}_financials"
            fetch_response = self.index.fetch(ids=[f"{ticker}_financials"])
            
            if not fetch_response.vectors:
                logger.info(f"[{ticker}] No cache found in Pinecone.")
                return True # Missing
                
            vector = fetch_response.vectors[f"{ticker}_financials"]
            ts_str = vector.metadata.get("timestamp", "2000-01-01T00:00:00")
            last_pushed = datetime.fromisoformat(ts_str)
            
            if datetime.now() - last_pushed > timedelta(hours=config.CACHE_TTL_HOURS):
                 logger.info(f"[{ticker}] Cache stale (Last: {ts_str}). Needs refresh.")
                 return True
            
            logger.info(f"[{ticker}] Cache fresh (Last: {ts_str}). using DB.")
            return False
            
        except Exception as e:
            logger.error(f"Error checking staleness: {e}")
            return True

    def fetch_cached_financials(self, ticker: str) -> Optional[Dict]:
        """Fetches the full structured JSON stored in metadata."""
        if self.mode == "MOCK":
             # Return None to trigger 'scrape' workflow, or return Mock Object
             return None
        
        try:
            res = self.index.fetch(ids=[f"{ticker}_financials"])
            if res.vectors:
                # Assuming we store the huge JSON string in metadata 'blob' or individual fields
                # Ideally, for huge JSONs, we'd fetch from Blob Storage (S3/GCS) and Pinecone just holds the pointer.
                # For this demo, we'll try to extract from metadata fields.
                meta = res.vectors[f"{ticker}_financials"].metadata
                return {
                    "financials": meta.get("financials_json"), # simplified
                    "risk": meta.get("risk_json")
                }
        except Exception as e:
            logger.error(f"Error fetching cache: {e}")
        return None

    def upsert_financials(self, ticker: str, data: dict):
        """
        Upserts structured financial data into Pinecone.
        Stores the full JSON blob in metadata for retrieval.
        """
        if self.mode == "MOCK":
            logger.info(f"[{ticker}] MOCK Upsert: Data saved to virtual index.")
            return

        try:
            # We use a dummy vector for the financial record itself (or an embedding of the profile)
            # For simplicity, we use a zero-vector or random vector if we don't have an embedding model yet.
            # In a real app, we'd embed the 'profile' text.
            dummy_vector = [0.1] * 1536 # Assuming OpenAI dims
            
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "financials_json": json.dumps(data.get("financials", {})), # Store as string
                "risk_json": json.dumps(data.get("risk", {})),
                "type": "financials",
                "ticker": ticker
            }
            
            self.index.upsert(vectors=[
                (f"{ticker}_financials", dummy_vector, metadata)
            ])
            logger.info(f"[{ticker}] Successfully upserted financials to Pinecone.")
            
        except Exception as e:
            logger.error(f"Error upserting to Pinecone: {e}")

    def upsert_vectors(self, vectors: List[tuple]):
        """
        Upserts raw vectors to Pinecone.
        Format: [(id, values, metadata), ...]
        """
        if self.mode == "MOCK":
            logger.info(f"MOCK Upsert: {len(vectors)} vectors saved.")
            return

        try:
            self.index.upsert(vectors=vectors)
            logger.info(f"Successfully upserted {len(vectors)} vectors to Pinecone.")
        except Exception as e:
            logger.error(f"Error upserting vectors: {e}")
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

    def resolve_ticker(self, company_name: str) -> Optional[Dict]:
        """
        Attempts to resolve a company name to a ticker using cached mappings in Pinecone.
        We search for the name in the metadata of 'ticker_mapping' type records.
        """
        logger.info(f"[{self.mode}] Resolving ticker for '{company_name}' via DB...")
        
        if self.mode == "MOCK":
            return None # Force dynamic resolution in mock if not explicitly testing DB
            
        try:
            # Concept: We strictly should use vector search for fuzzy matching on name, 
            # but for exact match or 'contains', we can use metadata filtering if we indexed it that way.
            # Here we assume we use vector search on the company name to find the best match.
            # Generate dummy vector for query (in real app, use embedding model)
            query_vector = [0.1] * 1536 
            
            res = self.index.query(
                vector=query_vector, 
                top_k=1, 
                include_metadata=True,
                filter={"type": "ticker_mapping"}
            )
            
            if res.matches:
                match = res.matches[0]
                # Simple check: In real app, check similarity score
                meta = match.metadata
                cached_name = meta.get("company_name", "").lower()
                
                # Loose check if query is substring of cached name or vice versa
                if company_name.lower() in cached_name or cached_name in company_name.lower():
                    logger.info(f"Resolved '{company_name}' to {meta.get('ticker')} ({meta.get('exchange')}) from DB.")
                    return {
                        "ticker": meta.get("ticker"),
                        "exchange": meta.get("exchange"),
                        "company_name": meta.get("company_name")
                    }
                    
        except Exception as e:
            logger.error(f"Error resolving ticker from DB: {e}")
            
        return None

    def cache_ticker(self, company_name: str, ticker: str, exchange: str):
        """
        Saves a resolved Ticker <-> Company Name mapping to Pinecone.
        """
        if self.mode == "MOCK":
            logger.info(f"MOCK: Cached mapping '{company_name}' -> {ticker}")
            return

        try:
            metadata = {
                "type": "ticker_mapping",
                "ticker": ticker,
                "exchange": exchange,
                "company_name": company_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Use name hash or similar as ID to avoid duplicates? 
            # ID: "mapping_{ticker}" to ensure one mapping per ticker? 
            # Or "mapping_{clean_name}"?
            # Let's use "mapping_{ticker}" to keep it unique per company entity
            
            dummy_vector = [0.1] * 1536
            
            self.index.upsert(vectors=[
                (f"mapping_{ticker}", dummy_vector, metadata)
            ])
            logger.info(f"Cached mapping for {company_name} ({ticker}) in DB.")
            
        except Exception as e:
            logger.error(f"Error caching ticker: {e}")

    def _get_mock_chunks(self) -> List[str]:
        """Returns mock report chunks for RAG simulation."""
        return [
            "Note 14 (Sukuk): The Group has issued a US$ 750 million Sukuk maturing in September 2025. The profit rate is fixed at 4.5%...",
            "Segment Reporting: The International Business generated AED 12 billion in revenue, driven by strong export growth in the Asian market...",
            "Risk Factors: The Group is exposed to interest rate risk primarily arising from its core lending activities..."
        ]
