import logging
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.pinecone_client import PineconeConnector

logger = logging.getLogger(__name__)

class VectorizerAgent:
    """
    Agent 3: The Knowledge Manager (RAG).
    Chunks documents and upserts to Pinecone.
    """
    def __init__(self):
        self.pc = PineconeConnector()

    def run(self, state: AgentState) -> AgentState:
        logger.info("Vectorizer: Indexing documents...")
        logs = state.get("logs", [])
        
        # In a real scenario, we would download PDFs from state['doc_urls']
        # and use unstructured.io to partition them.
        
        # Simulating Chunking & Upsert
        documents = [
            f"Financial Report for {state.get('company_name', 'Company')}",
            "Risk Factors: Market volatility and interest rate exposure.",
            "Outlook: Positive growth expected in GCC region."
        ]
        
        success = self.pc.upsert(documents, [{"type": "report"} for _ in documents])
        
        if success:
            logs.append("Vectorizer: Upserted 3 document chunks to Pinecone.")
        else:
            logs.append("Vectorizer: Failed to upsert documents.")
            
        return {
            "vector_ids": ["id_1", "id_2", "id_3"],
            "logs": logs
        }
