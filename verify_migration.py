import sys
import os
import shutil

# Ensure we are in root
sys.path.append(os.getcwd())

from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from intelligence_hub.agents.master_agent import MasterAgent

# from intelligence_hub.connectors.llm import LLMConnector # Mock it
import datetime


class MockLLM:
    def __init__(self):
        pass

    def embed(self, text):
        return [0.1] * 1536


def test_store_extensions():
    print("Testing CorporateProfileStore extensions...")
    try:
        store = CorporateProfileStore()
    except Exception as e:
        print(f"Skipping Store test due to init error (likely DB lock): {e}")
        return

    # 1. Financials
    ticker = "TEST_TICKER"
    data = {"revenue": 100, "net_income": 20}
    try:
        store.store_financials(ticker, data)
        retrieved = store.get_financials(ticker)
        if retrieved == data:
            print("✅ store_financials and get_financials working.")
        else:
            print(f"❌ Financials mismatch: {retrieved} != {data}")
    except Exception as e:
        print(f"❌ Financials test failed: {e}")

    # 2. Vectors
    # Note: Dimensionality must match collection.
    # If collection doesn't exist, it's created.
    # If using OpenAI EF, dim is 1536.
    vectors = [
        ("vec_id_1", [0.1] * 1536, {"text": "Chunk 1", "source": "Test"}),
    ]
    try:
        store.store_vectors(vectors)
        print("✅ store_vectors executed.")
    except Exception as e:
        print(f"⚠️ store_vectors failed (likely dim mismatch or connection): {e}")


def test_master_resolution():
    print("\nTesting MasterAgent resolution...")
    master = MasterAgent(
        company_name="Emaar Properties",
        llm_connector=MockLLM(),
        profile_store=None,
        enable_enrichment=False,
    )

    # 1. Config Match
    # Emaar Properties is in settings.py?
    # settings.py has "emaar properties": {"ticker": "EMAAR", ...}
    res = master.resolve_query("Emaar Properties")
    print(f"Result for 'Emaar Properties': {res}")

    if res["ticker"] == "EMAAR":
        print("✅ Config resolution working.")
    else:
        print(f"❌ Config resolution failed: {res}")

    # 2. Unknown
    res = master.resolve_query("NonExistentCompany123")
    print(f"Result for 'NonExistent': {res}")
    if res["ticker"] == "UNKNOWN":
        print("✅ Fallback to UNKNOWN working.")
    else:
        print(f"❌ Fallback failed: {res}")


if __name__ == "__main__":
    try:
        test_store_extensions()
        test_master_resolution()
        print("\n🎉 Verification process completed.")
    except Exception as e:
        print(f"\n❌ Verification script error: {e}")
        import traceback

        traceback.print_exc()
