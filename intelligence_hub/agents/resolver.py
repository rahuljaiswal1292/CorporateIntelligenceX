import logging
from intelligence_hub.graph.state import AgentState

logger = logging.getLogger(__name__)

class ResolverAgent:
    """
    Agent 1: The Resolver.
    Maps user query to Entity, Ticker, and Exchange.
    """
    def run(self, state: AgentState) -> AgentState:
        query = state["query"].lower()
        logger.info(f"Resolver: Resolving '{query}'...")
        
        # Mock Resolution Logic (In real app, use Google Search / ADX Search)
        if "emaar" in query:
            return {
                "ticker": "EMAAR", 
                "company_name": "Emaar Properties PJSC", 
                "exchange": "DFM",
                "website": "https://www.emaar.com",
                "logs": state.get("logs", []) + [f"Resolved '{query}' to Emaar Properties (DFM: EMAAR)"]
            }
        elif "nbd" in query or "emirates" in query:
             return {
                "ticker": "ENBD", 
                "company_name": "Emirates NBD Bank PJSC", 
                "exchange": "DFM",
                "website": "https://www.emiratesnbd.com",
                "logs": state.get("logs", []) + [f"Resolved '{query}' to Emirates NBD (DFM: ENBD)"]
            }
        elif "etisalat" in query or "e&" in query:
            return {
                "ticker": "EAND", 
                "company_name": "Emirates Telecommunications Group", 
                "exchange": "ADX",
                "website": "https://www.eand.com",
                "logs": state.get("logs", []) + [f"Resolved '{query}' to e& (ADX: EAND)"]
            }
        else:
             return {
                "ticker": "UNKNOWN", 
                "company_name": query.title(), 
                "exchange": "UNKNOWN",
                "website": "",
                "logs": state.get("logs", []) + [f"Could not resolve '{query}'. Assuming private/unlisted."]
            }
