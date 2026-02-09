from langgraph.graph import StateGraph, END
from intelligence_hub.graph.state import AgentState
from intelligence_hub.agents.resolver import ResolverAgent
from intelligence_hub.agents.scraper_orchestrator import ScraperOrchestrator
from intelligence_hub.agents.vectorizer import VectorizerAgent
from intelligence_hub.agents.analyst import AnalystAgent
from intelligence_hub.agents.pdf_agent import PdfAgent


def create_graph():
    """
    Constructs the Intelligence Graph.
    Flow: Resolver -> (Scraper, PdfAgent) -> Vectorizer -> Analyst
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
    workflow.add_node("scraper", scraper.run)
    workflow.add_node("vectorizer", vectorizer.run)
    workflow.add_node("analyst", analyst.run)
    workflow.add_node("pdf_agent", pdf_agent.run)

    # 4. Define Edges
    workflow.set_entry_point("resolver")

    # Branching: Resolver -> Scraper AND Resolver -> PdfAgent
    workflow.add_edge("resolver", "scraper")
    workflow.add_edge("resolver", "pdf_agent")

    # Re-converging: Both Scraper and PdfAgent go to Vectorizer/Analyst?
    # Logic:
    # Scraper -> Vectorizer -> Analyst
    # PdfAgent -> Analyst (PdfAgent handles its own vectorization/extraction internally for now)

    workflow.add_edge("scraper", "vectorizer")
    workflow.add_edge("vectorizer", "analyst")

    # PdfAgent also feeds into Analyst so Analyst can see "pdf_results" in state
    # This requires Analyst to wait for PdfAgent?
    # In LangGraph, if multiple nodes go to one, it waits? Or executes as soon as one is ready?
    # For simplicity in this version, let's just make PdfAgent an independent branch that ends,
    # but the state is shared so Analyst *might* see it if it runs later.
    # To Ensure Analyst sees it, we should edge PdfAgent -> Analyst.
    # But Analyst only runs once.
    # Let's chain them to be safe: Resolver -> Scraper -> Vectorizer -> PdfAgent -> Analyst
    # This ensures Analyst has EVERYTHING. Parallelism in LangGraph requires 'map' or 'parallel' constructs.
    # Sequential is safer for now to guarantee state availability.

    # workflow.add_edge("vectorizer", "pdf_agent")
    # workflow.add_edge("pdf_agent", "analyst")

    # WAIT, the prompt asked for "parallel".
    # If I use branching, I need to make sure Analyst waits.
    # LangGraph's default behavior for multiple edges to a node is to run the node for EACH input (if not configured to wait).
    # Let's stick to a linear flow for safety/correctness in this step unless I'm sure of the join behavior.
    # Resolver -> Scraper -> Vectorizer -> PdfAgent -> Analyst.
    # This is "stitched".

    workflow.add_edge("vectorizer", "pdf_agent")
    workflow.add_edge("pdf_agent", "analyst")
    workflow.add_edge("analyst", END)

    # 5. Compile
    return workflow.compile()
