import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from intelligence_hub.core.mock_data import get_company_data

def test_mock_fallback():
    print("Testing Mock Data Fallback...")
    
    # Test Agithia (Should be Generic)
    res = get_company_data("AGITHIA")
    print(f"Query: AGITHIA -> Name: {res['meta']['name']}, Ticker: {res['meta']['ticker']}")
    
    assert res['meta']['ticker'] == "UNKNOWN"
    assert "Etisalat" not in res['meta']['name']
    
    # Test Etisalat (Should be EAND)
    res_e = get_company_data("Etisalat")
    print(f"Query: Etisalat -> Name: {res_e['meta']['name']}, Ticker: {res_e['meta']['ticker']}")
    assert res_e['meta']['ticker'] == "EAND"

    # Test E& (Should be EAND)
    res_e2 = get_company_data("E&")
    print(f"Query: E& -> Name: {res_e2['meta']['name']}, Ticker: {res_e2['meta']['ticker']}")
    assert res_e2['meta']['ticker'] == "EAND"
    
    print("SUCCESS: Default fallback works as expected.")

if __name__ == "__main__":
    test_mock_fallback()
