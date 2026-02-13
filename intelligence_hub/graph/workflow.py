import os
import chromadb
from langgraph.graph import StateGraph, END
from intelligence_hub.graph.state import AgentState
from intelligence_hub.graph.state import AgentState

# from intelligence_hub.agents.resolver import ResolverAgent (Removed)
from intelligence_hub.agents.scraper_orchestrator import ScraperOrchestrator
from intelligence_hub.agents.vectorizer import VectorizerAgent
from intelligence_hub.agents.analyst import AnalystAgent
from intelligence_hub.agents.pdf_agent import PdfAgent
from intelligence_hub.agents.master_agent import MasterAgent
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from intelligence_hub.config.config import CHROMADB_PERSIST_DIRECTORY


def run_enrichment_node(state: AgentState):
    """
    Executes the Master Coordination Agent for profile enrichment.
    """
    company_name = state.get("company_name") or state.get("query", "Unknown")
    logs = state.get("logs", [])

    logs.append(f"Starting enrichment (and resolution) for {company_name}...")

    try:
        # Initialize dependencies
        store = CorporateProfileStore()
        llm_connector = LLMConnector()

        # Log collector
        def log_handler(msg):
            logs.append(msg.strip())
            print(msg.strip())

        # Initialize Master Agent
        agent = MasterAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
        )

        # Run agent
        result = agent.run(state)

        # Extract data
        full_profile = result.get("data", {})
        metadata = result.get("metadata", {})
        canonical_name = metadata.get("canonical_name", company_name)

        # Extract resolution info
        ticker = metadata.get("ticker", state.get("ticker"))
        exchange = metadata.get("exchange", state.get("exchange"))
        website = metadata.get("website", state.get("website"))

        logs.append(f"Enrichment completed. Canonical Name: {canonical_name}")

        return {
            "enrichments": full_profile,
            "company_name": canonical_name,
            "ticker": ticker,
            "exchange": exchange,
            "website": website,
            "logs": logs,
        }

    except Exception as e:
        logs.append(f"Enrichment failed: {str(e)}")
        return {"logs": logs, "enrichments": {"error": str(e)}}


def create_graph():
    """
    Constructs the Intelligence Graph.
    Flow: Resolver -> MasterEnrichment -> (Scraper, PdfAgent) -> Vectorizer -> Analyst
    """
    # 1. Initialize shared dependencies
    llm_connector = LLMConnector()
    store = CorporateProfileStore(persist_directory=CHROMADB_PERSIST_DIRECTORY)

    # 2. Initialize Agents
    # 2. Initialize Agents
    # resolver = ResolverAgent() (Removed)
    scraper = ScraperOrchestrator()
    vectorizer = VectorizerAgent()

    # Initialize agents that need llm_connector and profile_store
    # Note: company_name will be updated from state during execution
    analyst = AnalystAgent(
        company_name="placeholder",  # Will be updated from state
        llm_connector=llm_connector,
        profile_store=store,
    )
    pdf_agent = PdfAgent(
        company_name="placeholder",  # Will be updated from state
        llm_connector=llm_connector,
        profile_store=store,
    )

    # 2. Define Graph
    workflow = StateGraph(AgentState)

    # 3. Add Nodes
    # 3. Add Nodes
    # workflow.add_node("resolver", resolver.run) (Removed)
    workflow.add_node("master_enrichment", run_enrichment_node)
    workflow.add_node("scraper", scraper.run)
    workflow.add_node("vectorizer", vectorizer.run)
    workflow.add_node("analyst", analyst.run)
    workflow.add_node("pdf_agent", pdf_agent.run)

    # 4. Define Edges
    workflow.set_entry_point("master_enrichment")

    # Sequence: (Resolver removed) MasterEnrichment starts
    # workflow.add_edge("resolver", "master_enrichment")

    # Serialized Execution to avoid State merging conflicts:
    # MasterEnrichment -> Scraper -> PdfAgent -> Vectorizer -> Analyst
    workflow.add_edge("master_enrichment", "scraper")
    workflow.add_edge("scraper", "pdf_agent")
    workflow.add_edge("pdf_agent", "vectorizer")
    workflow.add_edge("vectorizer", "analyst")

    # Analyst is the end
    workflow.add_edge("analyst", END)

    # 5. Compile
    return workflow.compile()
