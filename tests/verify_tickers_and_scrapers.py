import sys
import os
import asyncio
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intelligence_hub.agents.resolver import ResolverAgent
from intelligence_hub.scrapers.dfm import DFMScraper
from intelligence_hub.scrapers.adx import ADXScraper

@patch('intelligence_hub.agents.resolver.PineconeConnector') # Patch usage in resolver
@patch('intelligence_hub.agents.resolver.ADXScraper')
@patch('intelligence_hub.agents.resolver.DFMScraper')
@patch('intelligence_hub.agents.resolver.ScrapingBeeConnector') 
def test_dynamic_resolution(MockSB, MockDFM, MockADX, MockPinecone):
    print("=== Testing Dynamic Resolution & Caching ===")
    
    # Setup Mocks
    mock_db = MockPinecone.return_value
    mock_adx = MockADX.return_value
    mock_dfm = MockDFM.return_value
    
    resolver = ResolverAgent()
    
    # Scenario 1: First Search for "Salik" (Unknown)
    # Expected: 
    # - DB Miss
    # - ADX/DFM Search Triggered
    # - Found on DFM (Simulated)
    # - Upsert to DB
    
    # Helper for async mock
    def async_return(result):
        f = asyncio.Future()
        f.set_result(result)
        return f
        
    print("\n--- 1. First Search (Cold Cache) ---")
    mock_db.resolve_ticker.return_value = None # Cache Miss
    
    # Simulate finding it on DFM (so ADX misses, DFM hits)
    # Note: I need to verify which order my code checks.
    # Code checks ADX then DFM.
    mock_adx.search_ticker.return_value = async_return((None, None))
    # Wait, my test earlier said "Bayanat". Let's say Bayanat is ADX for simplicity in this test run?
    # Or stick to DFM? The previous valid mock in test instructions was "BAYANAT".
    # Let's make it ADX hit for simplicity of mocking.
    
    mock_adx.search_ticker.return_value = async_return(("BAYANAT", "Bayanat AI"))
    
    state_cold = {"query": "bayanat", "logs": []}
    res_cold = resolver.run(state_cold)
    
    print(f"Result: {res_cold['ticker']} ({res_cold['exchange']})")
    
    # Assertions
    mock_db.resolve_ticker.assert_called_with("bayanat") # Checked Cache
    mock_db.cache_ticker.assert_called_with("Bayanat AI", "BAYANAT", "ADX") # Cached it!
    
    print("\n--- 2. Second Search (Cache Hit) ---")
    # Simulate DB returning the cached value
    mock_db.resolve_ticker.return_value = {
        "ticker": "BAYANAT", 
        "company_name": "Bayanat AI", 
        "exchange": "ADX"
    }
    
    # Reset Scrapers to ensure they are NOT called
    mock_adx.search_ticker.reset_mock()
    mock_dfm.search_ticker.reset_mock()
    
    res_warm = resolver.run(state_cold)
    
    print(f"Result: {res_warm['ticker']} ({res_warm['exchange']})")
    
    mock_db.resolve_ticker.assert_called_with("bayanat")
    mock_adx.search_ticker.assert_not_called()
    mock_dfm.search_ticker.assert_not_called()
    print("Success: Served from Cache!")

def test_resolution_and_targeting():
    # Helper to run the patched test
    test_dynamic_resolution()

if __name__ == "__main__":
    test_resolution_and_targeting()
