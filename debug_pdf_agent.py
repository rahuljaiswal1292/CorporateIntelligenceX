import os
import sys
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligence_hub.agents.pdf_agent import PdfAgent
from intelligence_hub.connectors.llm import LLMConnector


def debug_log(msg, level="INFO"):
    print(f"[{level}] {msg}")


def debug_pdf_agent():
    print("Debugging PdfAgent (Vision Test)...")

    state = {"ticker": "EMAAR", "exchange": "DFM", "logs": []}

    # Init Real Agent
    llm = LLMConnector()
    # Pass debug_log as log_callback
    agent = PdfAgent(company_name="EMAAR", llm_connector=llm, log_callback=debug_log)

    # Execute
    print("Running execute...")
    result = agent.execute(state)

    print("\n--- Execution Result ---")
    data = result.get("data", [])
    for item in data:
        # Only print for the target file to reduce noise
        if "EMAAR_PFR__E_14_02_24.pdf" in item.get("source", ""):
            print(f"\nFile: {item.get('source')}")
            print(f"Analysis: {json.dumps(item.get('meta'), indent=2)}")
            print(f"Financials: {json.dumps(item.get('financials'), indent=2)}")


if __name__ == "__main__":
    debug_pdf_agent()
