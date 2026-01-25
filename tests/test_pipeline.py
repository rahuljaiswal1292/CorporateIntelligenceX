import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence_hub.agents.scraper_orchestrator import ScraperOrchestrator

def test_pipeline():
    print("Testing Real-Time Pipeline (Mock Mode)...")
    
    orch = ScraperOrchestrator()
    
    # Test 1: EMAAR (DFM)
    print("\n--- Test 1: EMAAR (DFM) ---")
    data = orch.scrape_data("EMAAR", "DFM", "Emaar Properties")
    print("Keys returned:", data.keys())
    print("Financials:", data.get("financials"))
    print("Sources:", data.get("sources"))

    # Test 2: FAB (ADX)
    print("\n--- Test 2: FAB (ADX) ---")
    data = orch.scrape_data("FAB", "ADX", "First Abu Dhabi Bank")
    print("Keys returned:", data.keys())
    
if __name__ == "__main__":
    test_pipeline()
