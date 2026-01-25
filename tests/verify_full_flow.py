import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence_hub.graph.workflow import create_graph

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_full_flow():
    print("Starting Full Pipeline Verification...")
    
    graph = create_graph()
    
    # Simulate User Query
    query = "Emirates NBD"
    print(f"Query: {query}")
    
    config = {"configurable": {"thread_id": "test_1"}}
    final_state = graph.invoke({"query": query, "logs": []}, config=config)
    
    # Validate Core Components
    
    # 1. Resolver
    ticker = final_state.get("ticker")
    print(f"\n Resolver: Identified Ticker -> {ticker}")
    assert ticker == "ENBD" or ticker == "Unknown", f"Unexpected ticker: {ticker}"
    
    # 2. Scraper Data
    scraped_data = final_state.get("financial_data", {})
    print(f"\n Scraper: Retrieved Data Keys -> {list(scraped_data.keys())}")
    
    # Check for financials (Mock or Real)
    financials = scraped_data.get("financials", {})
    if financials:
        print(f"   - Revenue: {financials.get('revenue', 'N/A')}")
        print(f"   - Net Income: {financials.get('net_income', 'N/A')}")
    else:
        print("   No Financials Found")
        
    # 3. Vectorizer (Logs Check)
    logs = final_state.get("logs", [])
    vectorizer_logs = [l for l in logs if "Vectorizer" in l]
    print(f"\n Vectorizer Logs: {len(vectorizer_logs)} entries")
    for l in vectorizer_logs:
        print(f"   - {l}")
        
    # 4. Analyst Insights
    insights = final_state.get("insights", [])
    print(f"\n Analyst: Generated {len(insights)} Insights")
    for i in insights:
        print(f"   - [{i.get('category')}] {i.get('finding')}")
        
    print("\n Verification Complete!")

if __name__ == "__main__":
    test_full_flow()
