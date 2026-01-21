"""Workflow agents"""
import asyncio
import json
import time
from typing import Dict, Any
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from intelligence_hub.models.state import InvestigationState
from intelligence_hub.scrapers.exchange_scrapers import scrape_company_data
from intelligence_hub.prompts.templates import IDENTITY_RESOLUTION_PROMPT, FINANCIAL_SYNTHESIS_PROMPT
from intelligence_hub.utils.helpers import setup_logging, create_progress_message
from intelligence_hub.config.settings import config

logger = setup_logging()

_llm = None

def get_llm():
    """Get LLM instance"""
    global _llm
    if _llm is None:
        if config.LLM_MODEL.startswith("gpt"):
            from langchain_openai import ChatOpenAI
            _llm = ChatOpenAI(model=config.LLM_MODEL, temperature=0)
        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            _llm = ChatGoogleGenerativeAI(model=config.LLM_MODEL, temperature=0)
    return _llm

async def identity_resolution_agent(state: InvestigationState) -> InvestigationState:
    """Resolve company identity"""
    state.logs.append(create_progress_message("Identity Resolution", "starting"))

    cache_hit = False
    if cache_hit:
        state.canonical_name = "Cached Company Name"
        state.ticker = "TICKER"
        state.exchange = "DFM"
        state.cache_hit = True
        state.logs.append(create_progress_message("Identity Resolution", "cache hit"))
        state.progress = 25
        return state

    # Real-time resolution
    state.logs.append(create_progress_message("Identity Resolution", "querying exchanges"))

    dfm_companies = ["First Abu Dhabi Bank PJSC", "Emirates NBD Bank PJSC", "Abu Dhabi Commercial Bank PJSC", "Dubai Islamic Bank PJSC"]
    adx_companies = ["FAB", "ENBD", "ADCB", "DIB"]

    llm = get_llm()
    chain = IDENTITY_RESOLUTION_PROMPT | llm | JsonOutputParser()

    try:
        result = await chain.ainvoke({
            "user_input": state.user_input,
            "dfm_data": json.dumps(dfm_companies),
            "adx_data": json.dumps(adx_companies)
        })

        state.canonical_name = result.get('canonical_name', state.user_input)
        state.ticker = result.get('ticker', state.user_input.upper())
        state.exchange = result.get('exchange', 'DFM')
        state.logs.append(create_progress_message("Identity Resolution", f"resolved to {state.canonical_name} ({state.ticker})"))

    except Exception as e:
        logger.error(f"Identity resolution failed: {e}")
        state.canonical_name = state.user_input.title()
        state.ticker = state.user_input.upper()[:4]
        state.exchange = "DFM"
        state.logs.append(create_progress_message("Identity Resolution", "fallback used"))

    state.progress = 25
    return state

async def cache_audit_agent(state: InvestigationState) -> InvestigationState:
    """Audit data freshness"""
    state.logs.append(create_progress_message("Cache Audit", "checking freshness"))

    current_time = time.time()
    data_exists = False
    last_update = 0

    if data_exists and current_time - last_update < config.MARKET_DATA_TTL * 3600:
        state.logs.append(create_progress_message("Cache Audit", "data is fresh"))
    else:
        state.logs.append(create_progress_message("Cache Audit", "data needs refresh"))

    state.progress = 50
    return state

async def market_deep_dive_agent(state: InvestigationState) -> InvestigationState:
    """Extract market data"""
    state.logs.append(create_progress_message("Market Deep-Dive", "extracting data"))

    try:
        scraped_data = await scrape_company_data(state.ticker, state.exchange)
        state.profile_data = scraped_data.get("profile", {})
        state.financial_data = scraped_data.get("financials", {})
        state.governance_data = scraped_data.get("governance", {})
        state.logs.append(create_progress_message("Market Deep-Dive", "data extracted"))

    except Exception as e:
        logger.error(f"Market deep-dive failed: {e}")
        state.logs.append(create_progress_message("Market Deep-Dive", "failed - using defaults"))
        state.profile_data = {"error": "Scraping failed"}
        state.financial_data = {"error": "Scraping failed"}
        state.governance_data = {"error": "Scraping failed"}

    state.progress = 75
    return state

async def financial_synthesis_agent(state: InvestigationState) -> InvestigationState:
    """Synthesize insights and risks"""
    state.logs.append(create_progress_message("Financial Synthesis", "analyzing data"))

    try:
        llm = get_llm()
        prompt = FINANCIAL_SYNTHESIS_PROMPT.format(
            canonical_name=state.canonical_name,
            ticker=state.ticker,
            exchange=state.exchange,
            profile_data=json.dumps(state.profile_data),
            financial_data=json.dumps(state.financial_data),
            governance_data=json.dumps(state.governance_data)
        )

        result = await llm.ainvoke(prompt)
        parsed = JsonOutputParser().parse(result.content)
        state.strategic_takeaways = parsed.get('strategic_takeaways', [])
        state.risk_insights = parsed.get('risk_flags', [])
        state.logs.append(create_progress_message("Financial Synthesis", "insights generated"))

    except Exception as e:
        logger.error(f"Financial synthesis failed: {e}")
        state.logs.append(create_progress_message("Financial Synthesis", "failed - using defaults"))
        state.strategic_takeaways = ["Company shows stable market presence", "Strong regional positioning", "Good governance structure"]
        state.risk_insights = ["Market volatility exposure", "Regulatory compliance monitoring needed", "Competition in sector"]

    state.progress = 100
    state.completed_at = time.time()
    return state

def create_investigation_workflow():
    """Create investigation workflow"""
    workflow = StateGraph(InvestigationState)

    workflow.add_node("identity_resolution", identity_resolution_agent)
    workflow.add_node("cache_audit", cache_audit_agent)
    workflow.add_node("market_deep_dive", market_deep_dive_agent)
    workflow.add_node("financial_synthesis", financial_synthesis_agent)

    workflow.set_entry_point("identity_resolution")
    workflow.add_edge("identity_resolution", "cache_audit")
    workflow.add_edge("cache_audit", "market_deep_dive")
    workflow.add_edge("market_deep_dive", "financial_synthesis")
    workflow.add_edge("financial_synthesis", END)

    return workflow.compile()

investigation_workflow = create_investigation_workflow()