from langgraph.graph import StateGraph, END
from intelligence_hub.graph.state import AgentState
from intelligence_hub.agents.resolver import ResolverAgent
from intelligence_hub.agents.scraper_orchestrator import ScraperOrchestrator
from intelligence_hub.agents.vectorizer import VectorizerAgent
from intelligence_hub.agents.analyst import AnalystAgent

def create_graph():
    """
    Constructs the Intelligence Graph.
    Flow: Resolver -> Scraper -> Vectorizer -> Analyst
    """
    # 1. Initialize Agents
    resolver = ResolverAgent()
    scraper = ScraperOrchestrator()
    vectorizer = VectorizerAgent()
    analyst = AnalystAgent()
    
    # 2. Define Graph
    workflow = StateGraph(AgentState)
    
    # 3. Add Nodes
    workflow.add_node("resolver", resolver.run)
    workflow.add_node("scraper", scraper.run)
    workflow.add_node("vectorizer", vectorizer.run)
    workflow.add_node("analyst", analyst.run)
    
    # 4. Define Edges (Sequential)
    workflow.set_entry_point("resolver")
    workflow.add_edge("resolver", "scraper")
    workflow.add_edge("scraper", "vectorizer")
    workflow.add_edge("vectorizer", "analyst")
    workflow.add_edge("analyst", END)
    
    # 5. Compile
    return workflow.compile()
