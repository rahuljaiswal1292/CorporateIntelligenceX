import os
import chromadb
from langgraph.graph import StateGraph, END
from intelligence_hub.graph.state import AgentState
from intelligence_hub.agents.resolver import ResolverAgent
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
    company_name = state.get("company_name", "Unknown")
    logs = state.get("logs", [])

    logs.append(f"Starting enrichment for {company_name}...")

    try:
        # Initialize dependencies
        # Initialize dependencies
        # Use default persist directory from config, consistently with other agents
        store = CorporateProfileStore()
        llm_connector = LLMConnector()

        # Initialize Master Agent with LLMConnector
        agent = MasterAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=print,
        )

        # Run agent with state
        result = agent.run(state)

        # Extract data
        full_profile = result.get("data", {})
        enrichments = full_profile.get("enrichments", {})
        canonical_name = full_profile.get("canonical_name", company_name)

        logs.append(f"Enrichment completed. Canonical Name: {canonical_name}")

        return {
            "enrichments": full_profile,  # Store the whole profile structure
            "company_name": canonical_name,  # Update canonical name if changed
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
    resolver = ResolverAgent()
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
    workflow.add_node("resolver", resolver.run)
    workflow.add_node("master_enrichment", run_enrichment_node)
    workflow.add_node("scraper", scraper.run)
    workflow.add_node("vectorizer", vectorizer.run)
    workflow.add_node("analyst", analyst.run)
    workflow.add_node("pdf_agent", pdf_agent.run)

    # 4. Define Edges
    workflow.set_entry_point("resolver")

    # Sequence: Resolver -> MasterEnrichment
    workflow.add_edge("resolver", "master_enrichment")

    # Serialized Execution to avoid State merging conflicts:
    # MasterEnrichment -> Scraper -> Vectorizer -> PdfAgent -> Analyst
    workflow.add_edge("master_enrichment", "scraper")
    workflow.add_edge("scraper", "vectorizer")
    workflow.add_edge("vectorizer", "pdf_agent")
    workflow.add_edge("pdf_agent", "analyst")

    # Analyst is the end
    workflow.add_edge("analyst", END)

    # 5. Compile
    return workflow.compile()
