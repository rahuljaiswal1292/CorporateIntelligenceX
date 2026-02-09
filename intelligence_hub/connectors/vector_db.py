import os
import logging
import json
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from intelligence_hub.connectors.llm import LLMConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDBConnector:
    """
    Connector for ChromaDB Vector DB (Local).
    """

    def __init__(self, collection_name: str = "corporate_intelligence"):
        # Local persistence
        data_path = os.path.join(os.getcwd(), "data", "chroma_db")
        self.client = chromadb.PersistentClient(path=data_path)

        self.collection_name = collection_name
        self.llm = LLMConnector()

        # Get or create collection
        # We can use the LLM's embedding function directly if wrapped,
        # but Chroma supports many built-ins. To keep it consistent with our LLMConnector,
        # we'll generate embeddings manually and pass them to Chroma,
        # OR we can wrap our LLMConnector as a Chroma EmbeddingFunction.
        # For simplicity/control, we'll embed manually in upsert/search.

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    def upsert_documents(self, documents: List[str], metadata: List[Dict]):
        """
        Embeds and upserts documents into ChromaDB.
        """
        logger.info(f"Upserting {len(documents)} documents to ChromaDB...")

        ids = []
        embeddings = []
        metadatas = []

        import uuid

        for i, doc in enumerate(documents):
            # Generate ID
            ids.append(str(uuid.uuid4()))

            # Generate Embedding
            emb = self.llm.embed(doc)
            embeddings.append(emb)

            # Metadata
            metadatas.append(metadata[i])

        self.collection.add(
            documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids
        )
        logger.info(f"Successfully upserted {len(documents)} documents.")

    def search(
        self, query: str, top_k: int = 3, filter_conditions: Optional[Dict] = None
    ) -> List[str]:
        """
        Searches the index for relevant chunks.
        """
        logger.info(f"Vector Search: '{query}'")

        query_vector = self.llm.embed(query)

        # Build filter
        where_filter = filter_conditions if filter_conditions else None

        results = self.collection.query(
            query_embeddings=[query_vector], n_results=top_k, where=where_filter
        )

        # Results is a dict with 'documents', 'ids', etc. which are lists of lists
        if results and results["documents"]:
            return results["documents"][0]
        return []
