import chromadb
from chromadb.config import Settings
import os


def inspect_chroma():
    # Path to your chroma_db folder
    persist_dir = os.path.join(os.getcwd(), "data", "chroma_db")

    if not os.path.exists(persist_dir):
        print(f"Directory {persist_dir} does not exist.")
        return

    client = chromadb.PersistentClient(path=persist_dir)
    collections = client.list_collections()

    print(f"\n--- ChromaDB Inspection ---")
    print(f"Location: {persist_dir}")
    print(f"Total Collections Found: {len(collections)}")

    for coll in collections:
        count = coll.count()
        print(f"\nCollection: {coll.name}")
        print(f"Total Chunks: {count}")

        if count > 0:
            # Peek at the first 3 entries
            results = coll.peek(limit=3)
            print("Sample Documents:")
            for i, doc in enumerate(results["documents"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                ticker = meta.get("ticker", "Unknown")
                source = meta.get("source", "Unknown")
                print(f"  [{i+1}] Ticker: {ticker} | Source: {source}")
                print(f"      Text: {doc[:100]}...")


if __name__ == "__main__":
    inspect_chroma()
