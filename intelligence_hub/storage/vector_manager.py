import os
import uuid
import re
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import textwrap

from intelligence_hub.config.config import (
    OPENAI_API_KEY,
    CHROMADB_PERSIST_DIRECTORY,
    PROCESSED_DATA_DIRECTORY,
    DEFAULT_LLM_PROVIDER,
)


class VectorManager:
    """
    Manages embedding and storage of cleaned documents into ChromaDB.
    Supports both OpenAI and Google Gemini embeddings.
    """

    def __init__(
        self,
        collection_name: str = None,
        provider: str = None,
        persist_directory: str = None,
    ):
        self.provider = provider or DEFAULT_LLM_PROVIDER
        if collection_name is None:
            collection_name = f"strategic_intel_{self.provider.lower()}"
        self.persist_directory = persist_directory or CHROMADB_PERSIST_DIRECTORY

        from chromadb.config import Settings

        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True,
            ),
        )

        # Set up embedding function
        if self.provider.lower() == "google":
            self.embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                api_key=os.getenv("GOOGLE_API_KEY"), model_name="models/embedding-001"
            )
        else:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=OPENAI_API_KEY, model_name="text-embedding-3-small"
            )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={
                "description": "Strategic intelligence documents for RAG",
                "hnsw:space": "cosine",
            },
        )

    def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        """Simple recursive-style chunking by sentences/paragraphs."""
        if not text:
            return []

        # First split by paragraphs
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # If a single paragraph is larger than chunk_size, split it by sentences
                if len(para) > chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub_chunk = ""
                    for sent in sentences:
                        if len(sub_chunk) + len(sent) < chunk_size:
                            sub_chunk += sent + " "
                        else:
                            chunks.append(sub_chunk.strip())
                            sub_chunk = sent + " "
                    current_chunk = sub_chunk
                else:
                    current_chunk = para + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def ingest_directory(self, ticker: str, directory_path: str):
        """Ingest all cleaned text files for a specific ticker."""
        path = Path(directory_path)
        if not path.exists():
            print(f"Directory {directory_path} not found.")
            return

        print(f"Ingesting ticker: {ticker} from {path}")

        all_docs = []
        all_metadatas = []
        all_ids = []

        for file_path in path.rglob("*_cleaned.txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract basic metadata from the header we wrote in DataCleaner
            # (Crude extraction for now)
            source_file = "unknown"
            if "SOURCE_FILE:" in content:
                match = re.search(r"SOURCE_FILE: (.*)", content)
                if match:
                    source_file = match.group(1)

            # Remove header for chunking if possible, but keeping it for context is also okay
            chunks = self.chunk_text(content)

            for i, chunk in enumerate(chunks):
                if not chunk or not chunk.strip():
                    continue
                doc_id = f"{ticker}_{file_path.stem}_{i}_{str(uuid.uuid4())[:8]}"
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metadatas.append(
                    {
                        "ticker": ticker.upper(),
                        "source": source_file,
                        "chunk_index": i,
                        "file_path": str(file_path),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        if all_ids:
            # Batch size for ChromaDB is usually large, but let's do 20 at a time for safety
            batch_size = 20
            for k in range(0, len(all_ids), batch_size):
                try:
                    self.collection.add(
                        ids=all_ids[k : k + batch_size],
                        documents=all_docs[k : k + batch_size],
                        metadatas=all_metadatas[k : k + batch_size],
                    )
                    print(
                        f"  Added batch {k//batch_size + 1}/{(len(all_ids)-1)//batch_size + 1}"
                    )
                except Exception as e:
                    print(f"  Error in batch {k//batch_size + 1}: {e}")
                    # If it's a specific document issue, we try one by one in this batch
                    for j in range(k, min(k + batch_size, len(all_ids))):
                        try:
                            self.collection.add(
                                ids=[all_ids[j]],
                                documents=[all_docs[j]],
                                metadatas=[all_metadatas[j]],
                            )
                        except Exception as e2:
                            print(f"    Failed single document {all_ids[j]}: {e2}")
                            print(f"    Content (first 100 chars): {all_docs[j][:100]}")
                            print(f"    Content Length: {len(all_docs[j])}")

        print(f"Successfully ingested {len(all_ids)} chunks for {ticker}")

    def query(self, ticker: str, question: str, n_results: int = 5) -> List[Dict]:
        """Perform a RAG query filtered by ticker."""
        results = self.collection.query(
            query_texts=[question],
            n_results=n_results,
            where={"ticker": ticker.upper()},
        )

        # Format results for easy consumption
        formatted = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                formatted.append(
                    {
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                    }
                )
        return formatted


import re

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest processed data into ChromaDB.")
    parser.add_argument("ticker", help="Ticker symbol (e.g., EMAAR)")
    parser.add_argument("dir", help="Directory of cleaned files")
    parser.add_argument("--provider", help="LLM Provider (openai or google)")

    args = parser.parse_args()

    vm = VectorManager(provider=args.provider)
    vm.ingest_directory(args.ticker, args.dir)
