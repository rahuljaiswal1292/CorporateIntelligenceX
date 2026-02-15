import os
import chromadb
from langgraph.graph import StateGraph, END
from intelligence_hub.graph.state import AgentState

# Agent imports
from intelligence_hub.agents.scraper_orchestrator import ScraperOrchestrator
from intelligence_hub.agents.vectorizer import VectorizerAgent
from intelligence_hub.agents.analyst import AnalystAgent
from intelligence_hub.agents.pdf_agent import PdfAgent
from intelligence_hub.agents.master_agent import MasterAgent
from intelligence_hub.agents.wikipedia_agent import WikipediaAgent
from intelligence_hub.agents.news_agent import NewsAgent
from intelligence_hub.agents.ded_agent import DEDAgent

# Connectors and storage
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from intelligence_hub.config.config import CHROMADB_PERSIST_DIRECTORY


def run_enrichment_node(state: AgentState):
    """
    Executes the Master Coordination Agent for profile enrichment.
    """
    company_name = state.get("company_name") or state.get("query", "Unknown")
    logs = []

    logs.append(f"Starting enrichment (and resolution) for {company_name}...")

    try:
        # Initialize dependencies
        store = CorporateProfileStore()
        
        # Extract LLM config from state (if provided by UI)
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)

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
        confidence = metadata.get("confidence", full_profile.get("confidence_score", 0))

        logs.append(f"Enrichment completed. Canonical Name: {canonical_name}")

        return {
            "enrichments": full_profile,
            "company_name": canonical_name,
            "canonical_name": canonical_name,  # Explicit for UI
            "confidence": confidence,
            "confidence_score": confidence,  # Explicit for UI
            "ticker": ticker,
            "exchange": exchange,
            "website": website,
            "logs": logs,
        }

    except Exception as e:
        logs.append(f"Enrichment failed: {str(e)}")
        return {"logs": logs, "enrichments": {"error": str(e)}}


def run_wikipedia_node(state: AgentState):
    """Executes Wikipedia Agent"""
    company_name = state.get("canonical_name") or state.get("company_name") or state.get("query", "Unknown")
    logs = []
    
    try:
        store = CorporateProfileStore()
        
        # Extract LLM config from state (if provided by UI)
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)
        
        def log_handler(msg):
            logs.append(msg.strip())
            print(msg.strip())
        
        agent = WikipediaAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
        )
        
        result = agent.run(state)
        logs.append(f"Wikipedia Agent: {result.get('status', 'unknown')}")
        
        return {"logs": logs, "enrichments": state.get("enrichments", {})}
    except Exception as e:
        logs.append(f"Wikipedia Agent failed: {str(e)}")
        return {"logs": logs}


def run_news_node(state: AgentState):
    """Executes News Agent"""
    company_name = state.get("canonical_name") or state.get("company_name") or state.get("query", "Unknown")
    logs = []
    
    try:
        store = CorporateProfileStore()
        
        # Extract LLM config from state (if provided by UI)
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)
        
        def log_handler(msg):
            logs.append(msg.strip())
            print(msg.strip())
        
        agent = NewsAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
        )
        
        result = agent.run(state)
        logs.append(f"News Agent: {result.get('status', 'unknown')}")
        
        return {"logs": logs, "enrichments": state.get("enrichments", {})}
    except Exception as e:
        logs.append(f"News Agent failed: {str(e)}")
        return {"logs": logs}


def run_ded_node(state: AgentState):
    """Executes DED Agent"""
    company_name = state.get("canonical_name") or state.get("company_name") or state.get("query", "Unknown")
    logs = []
    
    try:
        store = CorporateProfileStore()
        
        # Extract LLM config from state (if provided by UI)
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)
        
        def log_handler(msg):
            logs.append(msg.strip())
            print(msg.strip())
        
        agent = DEDAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
        )
        
        result = agent.run(state)
        logs.append(f"DED Agent: {result.get('status', 'unknown')}")
        
        return {"logs": logs, "enrichments": state.get("enrichments", {})}
    except Exception as e:
        logs.append(f"DED Agent failed: {str(e)}")
        return {"logs": logs}


def create_resolution_graph():
    """Graph 1: Canonical Resolution Only"""
    workflow = StateGraph(AgentState)
    workflow.add_node("master_enrichment", run_enrichment_node)
    workflow.set_entry_point("master_enrichment")
    workflow.add_edge("master_enrichment", END)
    return workflow.compile()


def create_enrichment_graph():
    """Graph 2: Enrichment and beyond"""
    # Initialize shared dependencies that don't need LLM
    store = CorporateProfileStore(persist_directory=CHROMADB_PERSIST_DIRECTORY)

    # Initialize Agents that don't use LLM
    scraper = ScraperOrchestrator()
    vectorizer = VectorizerAgent()
    
    # Create wrapper functions for agents that need LLM config from state
    def run_analyst_node(state: AgentState):
        """Wrapper for AnalystAgent that extracts LLM config from state"""
        company_name = state.get("canonical_name") or state.get("company_name") or state.get("query", "Unknown")
        
        # Extract LLM config from state
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)
        
        analyst = AnalystAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return analyst.run(state)
    
    def run_pdf_agent_node(state: AgentState):
        """Wrapper for PdfAgent that extracts LLM config from state"""
        company_name = state.get("canonical_name") or state.get("company_name") or state.get("query", "Unknown")
        
        # Extract LLM config from state
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)
        
        pdf_agent = PdfAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return pdf_agent.run(state)

    workflow = StateGraph(AgentState)
    
    # Nodes
    workflow.add_node("start_enrichment", lambda state: state)
    workflow.add_node("wikipedia", run_wikipedia_node)
    workflow.add_node("news", run_news_node)
    workflow.add_node("ded", run_ded_node)
    workflow.add_node("scraper", scraper.run)
    workflow.add_node("vectorizer", vectorizer.run)
    workflow.add_node("analyst", run_analyst_node)
    workflow.add_node("pdf_agent", run_pdf_agent_node)

    # Edges - Parallel Start
    workflow.set_entry_point("start_enrichment")
    
    workflow.add_edge("start_enrichment", "wikipedia")
    workflow.add_edge("start_enrichment", "news")
    workflow.add_edge("start_enrichment", "ded")
    
    # Convergence
    workflow.add_edge("wikipedia", "scraper")
    workflow.add_edge("news", "scraper")
    workflow.add_edge("ded", "scraper")
    
    # Sequential
    workflow.add_edge("scraper", "vectorizer")
    workflow.add_edge("vectorizer", "pdf_agent")
    workflow.add_edge("pdf_agent", "analyst")
    workflow.add_edge("analyst", END)
    
    return workflow.compile()
