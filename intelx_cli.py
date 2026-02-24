import argparse
import os
import chromadb
from collections import Counter
from dotenv import load_dotenv

# Load environment variables (for API keys)
load_dotenv()

# tabulate fallback for clean CLI output without dependencies
try:
    from tabulate import tabulate
except ImportError:

    def tabulate(data, headers, **kwargs):
        header_line = " | ".join(str(h) for h in headers)
        lines = [header_line, "-" * len(header_line)]
        for row in data:
            lines.append(" | ".join(str(r) for r in row))
        return "\n".join(lines)


def get_client():
    persist_dir = os.path.join(os.getcwd(), "data", "chroma_db")
    return chromadb.PersistentClient(path=persist_dir)


def list_summary():
    client = get_client()
    print(f"\n[IntelX CLI] Scanning Database: PersistentClient activated")

    collections = client.list_collections()
    if not collections:
        print("No collections found in database.")
        return

    for coll in collections:
        try:
            coll_name = coll.name
            count = coll.count()
            print(f"\n--- Collection: {coll_name} ({count} total chunks) ---")

            if count == 0:
                print("Empty collection.")
                continue

            # Get unique tickers
            results = coll.get(include=["metadatas"])
            tickers = Counter()
            for m in results["metadatas"]:
                t = m.get("ticker", "UNKNOWN")
                tickers[t] += 1

            data = [[t, count] for t, count in tickers.items()]
            print(tabulate(data, headers=["Ticker", "Chunks"], tablefmt="presto"))
        except Exception as e:
            print(f"Error reading collection {coll.name}: {e}")


def list_sources(ticker):
    client = get_client()
    ticker = ticker.upper()
    print(f"\n--- Knowledge Source Audit: {ticker} ---")

    try:
        coll = client.get_collection("strategic_intel_openai")
    except Exception:
        print("Required collection 'strategic_intel_openai' not found.")
        return

    results = coll.get(where={"ticker": ticker}, include=["metadatas"])

    sources = Counter()
    for m in results["metadatas"]:
        src = m.get("source", "Unknown")
        sources[src] += 1

    if not sources:
        print(f"No sources found for ticker: {ticker}")
        return

    data = [[count, src] for src, count in sources.most_common()]
    print(tabulate(data, headers=["Chunks", "Source File"], tablefmt="simple"))
    print(f"\nTotal Chunks Indexed: {sum(sources.values())}")


def query_db(ticker, text):
    ticker = ticker.upper()
    print(f"\n--- IntelX Strategic Analysis [{ticker}]: '{text}' ---")

    from intelligence_hub.agents.chat_agent import ChatAgent
    from intelligence_hub.llm.connector import LLMConnector
    from intelligence_hub.storage.vector_manager import VectorManager

    try:
        # Initialize the same stack used by the UI
        vm = VectorManager()
        llm = LLMConnector()
        agent = ChatAgent(company_name=ticker, llm_connector=llm, vector_manager=vm)

        with print_spinner("Synthesizing answer from intelligence vectors..."):
            response = agent.answer_query(query=text, ticker=ticker)

        print("\n[ANALYSIS]")
        print("-" * 50)
        print(response)
        print("-" * 50)

        # Also show sources for transparency
        coll = vm.collection
        results = coll.query(query_texts=[text], where={"ticker": ticker}, n_results=2)
        print("\nPrimary Sources Used:")
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            print(
                f" - {meta.get('source')} (Similarity: {1 - results['distances'][0][i]:.2%})"
            )

    except Exception as e:
        print(f"Analysis Error: {e}")


def print_spinner(text):
    import sys
    import threading
    import time

    class Spinner:
        def __init__(self, message):
            self.message = message
            self.stop_event = threading.Event()
            self.thread = threading.Thread(target=self._spin)

        def _spin(self):
            chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i = 0
            while not self.stop_event.is_set():
                sys.stdout.write(f"\r{chars[i % len(chars)]} {self.message}")
                sys.stdout.flush()
                time.sleep(0.1)
                i += 1
            sys.stdout.write("\r")

        def __enter__(self):
            self.thread.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.stop_event.set()
            self.thread.join()

    return Spinner(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IntelX Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Summary command
    subparsers.add_parser("summary", help="Show overview of all tickers in DB")

    # Audit command
    audit_parser = subparsers.add_parser(
        "audit", help="Audit sources for a specific ticker"
    )
    audit_parser.add_argument("ticker", help="Ticker symbol (e.g., EMAAR)")

    # Query command
    query_parser = subparsers.add_parser("query", help="Direct semantic search in DB")
    query_parser.add_argument("ticker", help="Ticker symbol")
    query_parser.add_argument("text", help="Search text")

    args = parser.parse_args()

    if args.command == "summary":
        list_summary()
    elif args.command == "audit":
        list_sources(args.ticker)
    elif args.command == "query":
        query_db(args.ticker, args.text)
    else:
        parser.print_help()
