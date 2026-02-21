import os
import asyncio
import nest_asyncio
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig

from intelligence_hub.graph.state import AgentState
from intelligence_hub.config.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    CHROMADB_PERSIST_DIRECTORY,
)

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

# Scraper imports
from intelligence_hub.scrapers.adx import ADXScraper
from intelligence_hub.scrapers.dfm import DFMScraper
from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector

# Connectors and storage
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore


def _llm_from_config(config: RunnableConfig) -> LLMConnector:
    """
    Build an LLMConnector from the run-level RunnableConfig.
    Reads from config["configurable"], falling back to app-level defaults
    then env vars inside LLMConnector itself.
    """
    cfg = config.get("configurable", {}) if config else {}
    return LLMConnector(
        model=cfg.get("llm_model", DEFAULT_LLM_MODEL),
        temperature=cfg.get("llm_temperature", 0.0),
        top_p=cfg.get("llm_top_p", 1.0),
        frequency_penalty=cfg.get("llm_frequency_penalty", 0.0),
    )


def run_enrichment_node(state: AgentState, config: RunnableConfig):
    """Executes the Master Coordination Agent for profile enrichment."""
    company_name = state.get("company_name") or state.get("query", "Unknown")
    logs = []
    logs.append(f"Starting enrichment (and resolution) for {company_name}...")

    try:
        store = CorporateProfileStore()
        llm_connector = _llm_from_config(config)

        def log_handler(msg):
            logs.append(msg.strip())
            print(msg.strip())

        agent = MasterAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
            log_callback=log_handler,
        )

        result = agent.run(state)

        full_profile = result.get("data", {})
        metadata = result.get("metadata", {})
        canonical_name = metadata.get("canonical_name") or company_name

        ticker = metadata.get("ticker", state.get("ticker"))
        exchange = metadata.get("exchange", state.get("exchange"))
        website = metadata.get("website", state.get("website"))
        confidence = metadata.get("confidence", full_profile.get("confidence_score", 0))

        if "enrichments" in full_profile:
            inner_enrichments = full_profile.pop("enrichments")
            full_profile.update(inner_enrichments)

        logs.append(f"Enrichment completed. Canonical Name: {canonical_name}")

        return {
            "enrichments": full_profile,
            "company_name": canonical_name,
            "canonical_name": canonical_name,
            "confidence": confidence,
            "confidence_score": confidence,
            "ticker": ticker,
            "exchange": exchange,
            "website": website,
            "logs": logs,
        }

    except Exception as e:
        logs.append(f"Enrichment failed: {str(e)}")
        return {"logs": logs, "enrichments": {"error": str(e)}}


def run_wikipedia_node(state: AgentState, config: RunnableConfig):
    """Executes Wikipedia Agent"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
    logs = []

    try:
        store = CorporateProfileStore()
        llm_connector = _llm_from_config(config)

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
        return {"logs": logs}

    except Exception as e:
        logs.append(f"Wikipedia Agent failed: {str(e)}")
        return {"logs": logs}


def run_news_node(state: AgentState, config: RunnableConfig):
    """Executes News Agent"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
    logs = []

    try:
        store = CorporateProfileStore()
        llm_connector = _llm_from_config(config)

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
        return {"logs": logs}

    except Exception as e:
        logs.append(f"News Agent failed: {str(e)}")
        return {"logs": logs}


def run_ded_node(state: AgentState, config: RunnableConfig):
    """Executes DED Agent"""
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
    logs = []

    try:
        store = CorporateProfileStore()
        llm_connector = _llm_from_config(config)

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
        return {"logs": logs}

    except Exception as e:
        logs.append(f"DED Agent failed: {str(e)}")
        return {"logs": logs}


def run_exchange_scraper_node(state: AgentState, config: RunnableConfig):
    """
    Exchange-routed scraper node.
    Reads `exchange` from state (set by resolution graph) and calls
    the matching scraper:
      - 'ADX' → ADXScraper.scrape_company(ticker)
      - 'DFM' → DFMScraper.scrape_company(ticker)
      - other  → falls back to ScraperOrchestrator (Yahoo + Wiki)
    Downloads are saved to data/<exchange>/<ticker>/ automatically.
    """
    ticker = state.get("ticker", "UNKNOWN")
    exchange = (state.get("exchange") or "UNKNOWN").upper()
    company_name = (
        state.get("canonical_name")
        or state.get("company_name")
        or state.get("query", "Unknown")
    )
    logs = []
    logs.append(f"Exchange Scraper: routing {ticker} → {exchange}")

    if ticker == "UNKNOWN":
        logs.append("Exchange Scraper: no ticker resolved, skipping exchange scrape.")
        return {"logs": logs, "financial_data": {}}

    def safe_async(coro):
        """Run an async coroutine from a synchronous LangGraph node."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        return loop.run_until_complete(coro)

    try:
        connector = WebScraperConnector()

        if exchange == "ADX":
            logs.append(f"Exchange Scraper: starting ADX scrape for {ticker}")
            scraper = ADXScraper(connector)
            data = safe_async(scraper.scrape_company(ticker))
            logs.append(f"Exchange Scraper: ADX scrape complete for {ticker}")

        elif exchange == "DFM":
            logs.append(f"Exchange Scraper: starting DFM scrape for {ticker}")
            scraper = DFMScraper(connector)
            data = safe_async(scraper.scrape_company(ticker))
            logs.append(f"Exchange Scraper: DFM scrape complete for {ticker}")

        else:
            logs.append(
                f"Exchange Scraper: unknown exchange '{exchange}', "
                "falling back to ScraperOrchestrator."
            )
            orchestrator = ScraperOrchestrator()
            result = orchestrator.run(state)
            return {**result, "logs": logs + result.get("logs", [])}

        # Normalise output shape
        doc_urls = [
            d.get("url", "") for d in data.get("documents", []) if isinstance(d, dict)
        ] or []
        return {
            "financial_data": data,
            "doc_urls": doc_urls,
            "logs": logs,
        }

    except Exception as e:
        logs.append(f"Exchange Scraper: error — {e}")
        return {"financial_data": {}, "logs": logs}


def create_resolution_graph():
    """Graph 1: Canonical Resolution Only (SerpAPI → canonical name + ticker + exchange).
    The graph pauses here; the UI shows the resolved name and waits for user confirmation.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("master_enrichment", run_enrichment_node)
    workflow.set_entry_point("master_enrichment")
    workflow.add_edge("master_enrichment", END)
    return workflow.compile()


def create_enrichment_graph():
    """Graph 2: Full enrichment pipeline triggered after user confirms resolution.
    Sequence:
      start → [wikipedia, news, ded] (parallel)
             → exchange_scraper       (ADX or DFM, based on state['exchange'])
             → pdf_agent
             → vectorizer
             → analyst
             → presentation_agent
    """
    store = CorporateProfileStore(persist_directory=CHROMADB_PERSIST_DIRECTORY)
    vectorizer = VectorizerAgent()

    def run_analyst_node(state: AgentState, config: RunnableConfig):
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or state.get("query", "Unknown")
        )
        llm_connector = _llm_from_config(config)
        analyst = AnalystAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return analyst.run(state)

    def run_pdf_agent_node(state: AgentState, config: RunnableConfig):
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or state.get("query", "Unknown")
        )
        llm_connector = _llm_from_config(config)
        pdf_agent = PdfAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return pdf_agent.run(state)

    def run_presentation_agent_node(state: AgentState, config: RunnableConfig):
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or state.get("query", "Unknown")
        )
        llm_connector = _llm_from_config(config)
        presentation_agent = PresentationAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            profile_store=store,
        )
        return presentation_agent.run(state)

    # Build graph
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("start_enrichment", lambda state, config: state)
    workflow.add_node("wikipedia", run_wikipedia_node)
    workflow.add_node("news", run_news_node)
    workflow.add_node("ded", run_ded_node)
    workflow.add_node("exchange_scraper", run_exchange_scraper_node)  # ADX/DFM routing
    workflow.add_node("vectorizer", vectorizer.run)
    workflow.add_node("analyst", run_analyst_node)
    workflow.add_node("pdf_agent", run_pdf_agent_node)
    workflow.add_node("presentation_agent", run_presentation_agent_node)

    # Parallel kick-off from start
    workflow.set_entry_point("start_enrichment")
    workflow.add_edge("start_enrichment", "wikipedia")
    workflow.add_edge("start_enrichment", "news")
    workflow.add_edge("start_enrichment", "ded")

    # All three converge into the exchange scraper
    workflow.add_edge("wikipedia", "exchange_scraper")
    workflow.add_edge("news", "exchange_scraper")
    workflow.add_edge("ded", "exchange_scraper")

    # Sequential pipeline after scraping
    workflow.add_edge("exchange_scraper", "pdf_agent")
    workflow.add_edge("pdf_agent", "vectorizer")
    workflow.add_edge("vectorizer", "analyst")
    workflow.add_edge("analyst", "presentation_agent")
    workflow.add_edge("presentation_agent", END)

    return workflow.compile()
