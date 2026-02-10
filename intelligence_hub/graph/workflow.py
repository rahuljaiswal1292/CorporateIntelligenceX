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
        chroma_client = chromadb.PersistentClient(path=CHROMADB_PERSIST_DIRECTORY)
        store = CorporateProfileStore(chroma_client)

        # Initialize Master Agent
        # We pass a simple print as log_callback for console, but we'll capture logs in state too
        agent = MasterAgent(
            company_name=company_name, profile_store=store, log_callback=print
        )

        # Run agent
        result = agent.run({"initial_query": state["query"]})

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
    # 1. Initialize Agents
    resolver = ResolverAgent()
    scraper = ScraperOrchestrator()
    vectorizer = VectorizerAgent()
    analyst = AnalystAgent()
    pdf_agent = PdfAgent()

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

    # Branching: MasterEnrichment -> Scraper AND MasterEnrichment -> PdfAgent
    # This ensures both downstream agents have the canonical company name
    workflow.add_edge("master_enrichment", "scraper")
    workflow.add_edge("master_enrichment", "pdf_agent")

    # Re-converging
    # Scraper path
    workflow.add_edge("scraper", "vectorizer")
    workflow.add_edge("vectorizer", "analyst")

    # PdfAgent path
    workflow.add_edge("pdf_agent", "analyst")

    # Analyst is the end
    workflow.add_edge("analyst", END)

    # 5. Compile
    return workflow.compile()
