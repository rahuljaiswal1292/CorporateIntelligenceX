import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence_hub.graph.workflow import create_graph

def test_sukoon_flow():
    print("Testing 'Sukoon Insurance' Flow...")
    
    graph = create_graph()
    
    query = "Sukoon Insurance"
    
    # Run Graph
    result = graph.invoke({"query": query, "logs": []})
    
    # 1. Resolver Check
    print(f"Ticker: {result.get('ticker')}")
    print(f"Company: {result.get('company_name')}")
    
    # 2. Scraper Check
    scraped = result.get("financial_data", {})
    sources = scraped.get("sources", [])
    print(f"Sources Found: {[s['title'] for s in sources]}")
    
    # 3. Data Check
    if any(s['title'] == 'Wikipedia' for s in sources):
        print("PASS: Wikipedia source found for unlisted entity.")
    else:
        print("FAIL: Wikipedia source NOT found.")
        
    logs = result.get("logs", [])
    print("\nLogs:")
    for l in logs:
        print(f"- {l}")

if __name__ == "__main__":
    test_sukoon_flow()
