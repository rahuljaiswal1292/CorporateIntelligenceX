import os
import chromadb
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from intelligence_hub.graph.state import AgentState

# Agent imports
from intelligence_hub.agents.scraper_orchestrator import ScraperOrchestrator
from intelligence_hub.agents.vectorizer import VectorizerAgent
from intelligence_hub.agents.analyst import AnalystAgent
from intelligence_hub.agents.pdf_agent import PdfAgent
from intelligence_hub.agents.master_agent import MasterAgent
from intelligence_hub.agents.presentation_agent import PresentationAgent
from intelligence_hub.agents.wikipedia_agent import WikipediaAgent
from intelligence_hub.agents.news_agent import NewsAgent
from intelligence_hub.agents.ded_agent import DEDAgent

# Connectors and storage
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from intelligence_hub.config.config import CHROMADB_PERSIST_DIRECTORY


def run_resolution_node(state: AgentState):
    """
    Phase 0: Canonical Resolution Only.
    Fast check via Config, DB, or Exchange Search.
    """
    query = state.get("query", "Unknown")
    logs = []

    logs.append(f"Resolving entity for: {query}")

    try:
        # Initialize dependencies
        store = CorporateProfileStore()

        # Initialize Master Agent (just for resolution)
        agent = MasterAgent(
            company_name=query,
            llm_connector=LLMConnector(config=state.get("llm_config", {})),
            profile_store=store,
            log_callback=lambda m: None,
        )

        # Run Phase 0
        resolution = agent.resolve_query(query)
        canonical_name = resolution.get("company_name", query)

        logs.append(f"Entity Resolved to: {canonical_name}")

        return {
            "canonical_name": canonical_name,
            "company_name": canonical_name,
            "ticker": resolution.get("ticker"),
            "exchange": resolution.get("exchange"),
            "website": resolution.get("website"),
            "description": resolution.get("description"),
            "logs": logs,
        }
    except Exception as e:
        logs.append(f"Resolution failed: {str(e)}")
        return {"logs": logs}


def run_profiling_node(state: AgentState):
    """
    Phase 1: Basic Profiling (SERP, Knowledge Graph).
    """
    company_name = state.get("canonical_name") or state.get("query", "Unknown")
    logs = []

    logs.append(f"Fetching profile for {company_name}...")

    try:
        store = CorporateProfileStore()
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)

        def log_handler(msg):
            logs.append(msg.strip())

        # Initialize Master Agent - disable heavy enrichment for initial resolution
        agent = MasterAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
            enable_enrichment=False,  # Defer heavy enrichment to parallel nodes
        )

        # Run Phase 1
        result = agent.run_serpapi_phase(state)
        full_profile = result.get("data", {})
        ticker = full_profile.get("ticker", state.get("ticker"))
        exchange = full_profile.get("exchange", state.get("exchange"))
        website = full_profile.get("website", state.get("website"))
        confidence = full_profile.get("confidence_score", 0)

        # Extract resolution info
        # ticker = metadata.get("ticker", state.get("ticker"))
        # exchange = metadata.get("exchange", state.get("exchange"))
        # website = metadata.get("website", state.get("website"))
        # confidence = metadata.get("confidence", full_profile.get("confidence_score", 0))

        if "enrichments" in full_profile:
            inner_enrichments = full_profile.pop("enrichments")
            full_profile.update(inner_enrichments)

        logs.append(f"Enrichment completed. Canonical Name: {company_name}")

        return {
            "enrichments": full_profile,
            "canonical_name": company_name,
            "confidence": confidence,
            "confidence_score": confidence,
            "ticker": ticker,
            "exchange": exchange,
            "website": website,
            "logs": logs,
        }

    except Exception as e:
        logs.append(f"Profiling failed: {str(e)}")
        return {"logs": logs}


def run_wikipedia_node(state: AgentState):
    """Executes Wikipedia Agent"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
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

        return {
            "logs": logs,
            "enrichments": (
                {"wikipedia": result.get("data")}
                if result.get("status") == "completed"
                else {}
            ),
        }
    except Exception as e:
        logs.append(f"Wikipedia Agent failed: {str(e)}")

    # Only return logs — don't overwrite shared state fields that other parallel nodes own
    return {"logs": logs}


def run_news_node(state: AgentState):
    """Executes News Agent"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
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

        return {
            "logs": logs,
            "enrichments": (
                {"news": result.get("data")}
                if result.get("status") == "completed"
                else {}
            ),
        }
    except Exception as e:
        logs.append(f"News Agent failed: {str(e)}")

    return {"logs": logs}


def run_ded_node(state: AgentState):
    """Executes DED Agent"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
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

        return {
            "logs": logs,
            "enrichments": (
                {"uae_ded_license": result.get("data")}
                if result.get("status") == "completed"
                else {}
            ),
        }
    except Exception as e:
        logs.append(f"DED Agent failed: {str(e)}")

    return {"logs": logs}


def join_enrichment_node(state: AgentState):
    """
    Passthrough join node.

    LangGraph requires a single downstream node to collect the results of
    parallel branches. All three parallel enrichment agents (Wikipedia, News,
    DED) converge here before the scraper runs. Their individual log lines
    are merged automatically by the `Annotated[List, operator.add]` reducer
    defined on AgentState.logs, so this node has nothing extra to do.
    """
    return {"logs": ["Enrichment agents complete — starting scraper phase."]}


def run_competitor_analysis_node(state: AgentState):
    """Executes Competitor Analysis using MasterAgent's internal method"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
    logs = []

    try:
        store = CorporateProfileStore()
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)

        def log_handler(msg):
            logs.append(msg.strip())
            print(msg.strip())

        # Use MasterAgent just for its competitor analysis capability
        agent = MasterAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
            enable_enrichment=True,
        )

        competitor_results = agent.get_competitor_analysis(company_name)

        return {
            "logs": logs,
            "enrichments": {
                "Competitor Analysis": {"status": "success", "data": competitor_results}
            },
        }
    except Exception as e:
        logs.append(f"Competitor Analysis failed: {str(e)}")
        return {"logs": logs}


def create_resolution_graph():
    """Graph 1: Canonical Resolution Only"""
    workflow = StateGraph(AgentState)
    workflow.add_node("resolution", run_resolution_node)
    workflow.add_node("profiling", run_profiling_node)

    workflow.set_entry_point("resolution")
    workflow.add_edge("resolution", "profiling")
    workflow.add_edge("profiling", END)
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


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
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or state.get("query", "Unknown")
        )

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
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or state.get("query", "Unknown")
        )

        # Extract LLM config from state
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)

        pdf_agent = PdfAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return pdf_agent.run(state)

    def run_presentation_agent_node(state: AgentState):
        """Wrapper for PresentationAgent"""
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or state.get("query", "Unknown")
        )

        # Extract LLM config from state
        llm_config = state.get("llm_config", {})
        llm_connector = LLMConnector(config=llm_config)

        agent = PresentationAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return agent.run(state)

    workflow = StateGraph(AgentState)

    # ── Nodes ──────────────────────────────────────────────────────────────
    # start_enrichment: lightweight pass-through that signals the graph entry.
    # Must return a dict (even if empty) — never pass the full state object.
    workflow.add_node(
        "start_enrichment", lambda state: {"logs": ["Starting enrichment phase..."]}
    )

    # Parallel enrichment agents
    workflow.add_node("wikipedia", run_wikipedia_node)
    workflow.add_node("news", run_news_node)
    workflow.add_node("ded", run_ded_node)
    workflow.add_node("competitors", run_competitor_analysis_node)

    # ── FAN-IN fix: explicit join node ────────────────────────────────────
    # LangGraph cannot compile a graph where multiple edges arrive at the
    # same node from different branches without a declared join.  Adding
    # `join_enrichment` as the single target of all three parallel branches
    # resolves the compilation error.
    workflow.add_node("join_enrichment", join_enrichment_node)

    def run_scraper_node(state: AgentState):
        """Wrapper for scraper.run"""
        return scraper.run(state)

    # Sequential post-enrichment nodes
    workflow.add_node("scraper", run_scraper_node)
    workflow.add_node("vectorizer", lambda state: vectorizer.run(state))
    workflow.add_node("analyst", run_analyst_node)
    workflow.add_node("pdf_agent", run_pdf_agent_node)
    workflow.add_node("presentation_agent", run_presentation_agent_node)

    # Sequence: (Resolver removed) MasterEnrichment starts

    # ── Edges ──────────────────────────────────────────────────────────────
    workflow.set_entry_point("start_enrichment")

    # Fan-out: start_enrichment → all parallel enrichment nodes
    workflow.add_edge("start_enrichment", "wikipedia")
    workflow.add_edge("start_enrichment", "news")
    workflow.add_edge("start_enrichment", "ded")
    workflow.add_edge("start_enrichment", "competitors")

    # Convergence
    workflow.add_edge("wikipedia", "scraper")
    workflow.add_edge("news", "scraper")
    workflow.add_edge("ded", "scraper")
    workflow.add_edge("competitors", "scraper")

    # Sequential
    workflow.add_edge("scraper", "pdf_agent")
    workflow.add_edge("pdf_agent", "vectorizer")
    workflow.add_edge("vectorizer", "analyst")
    workflow.add_edge("analyst", "presentation_agent")
    workflow.add_edge("presentation_agent", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)
