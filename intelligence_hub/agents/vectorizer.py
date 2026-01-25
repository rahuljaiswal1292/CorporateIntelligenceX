import logging
import uuid
import datetime
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.pinecone_client import PineconeConnector
from intelligence_hub.connectors.llm import LLMConnector

logger = logging.getLogger(__name__)

class VectorizerAgent:
    """
    Agent 3: The Knowledge Manager (RAG).
    Chunks documents and upserts to Pinecone.
    """
    def __init__(self):
        self.pc = PineconeConnector()
        self.llm = LLMConnector()

    def run(self, state: AgentState) -> AgentState:
        logger.info("Vectorizer: Indexing documents...")
        logs = state.get("logs", [])
        
        scraped_data = state.get("financial_data", {})
        ticker = state.get("ticker", "UNKNOWN")
        sources = scraped_data.get("sources", [])
        
        vectors = []
        
        for source in sources:
            title = source.get("title", "Unknown Source")
            # We look for 'raw_html_snippet' or 'content'
            content = source.get("raw_html_snippet") or source.get("content")
            
            if not content or len(content) < 50:
                continue
                
            # Simple Chunking (Split by paragraphs for now)
            # In a robust system, we'd use LangChain's RecursiveCharacterTextSplitter
            chunks = [c.strip() for c in content.split('\n\n') if len(c.strip()) > 100]
            
            for i, chunk in enumerate(chunks[:20]): # Limit to 20 chunks per source to avoid overload
                try:
                    vector_values = self.llm.embed(chunk)
                    chunk_id = f"{ticker}_{uuid.uuid4()}"
                    
                    metadata = {
                        "text": chunk[:1000], # Store text in metadata for retrieval
                        "source": title,
                        "ticker": ticker,
                        "type": "chunk",
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    
                    vectors.append((chunk_id, vector_values, metadata))
                except Exception as e:
                    logger.error(f"Error embedding chunk: {e}")

        if vectors:
            self.pc.upsert_vectors(vectors)
            logs.append(f"Vectorizer: Upserted {len(vectors)} chunks to Pinecone.")
        else:
            logs.append("Vectorizer: No valid text content found to index.")
            
        return {
            "logs": logs,
            # Preserving state
            "ticker": ticker,
            "company_name": state.get("company_name"),
            "financial_data": scraped_data
        }
