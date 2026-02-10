import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from intelligence_hub.graph.workflow import create_graph
from intelligence_hub.config.config import SERPAPI_API_KEY, OPENAI_API_KEY


def verify_workflow():
    print("Verifying workflow compilation...")
    try:
        app = create_graph()
        print("✅ Workflow compiled successfully.")
    except Exception as e:
        print(f"❌ Workflow compilation failed: {e}")
        return

    print("\nVerifying environment variables...")
    print(f"SERPAPI_API_KEY: {'✅ Present' if SERPAPI_API_KEY else '❌ Missing'}")
    print(f"OPENAI_API_KEY: {'✅ Present' if OPENAI_API_KEY else '❌ Missing'}")

    # Don't actually run the graph fully as it might consume APIs,
    # but we can check if agents are importable.
    print("\nVerifying agent imports...")
    try:
        from intelligence_hub.agents.master_agent import MasterAgent
        from intelligence_hub.agents.serpapi_profile_agent import SerpAPIProfileAgent
        from intelligence_hub.agents.wikipedia_agent import WikipediaAgent
        from intelligence_hub.agents.news_agent import NewsAgent
        from intelligence_hub.agents.ded_agent import DEDAgent

        print("✅ All agents imported successfully.")
    except ImportError as e:
        print(f"❌ Agent import failed: {e}")


if __name__ == "__main__":
    verify_workflow()
