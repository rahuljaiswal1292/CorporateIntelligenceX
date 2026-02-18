from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Shared state object for the Intelligence Graph.
    """

    # Inputs
    query: str

    # Resolver Outputs
    ticker: str
    company_name: str
    canonical_name: str # Added for UI consistency
    exchange: str  # ADX, DFM, or UNKNOWN
    website: str

    # Scraper Outputs
    financial_data: Dict[str, Any]  # Structured financials
    raw_html: str
    doc_urls: List[str]

    # Vectorizer Outputs
    vector_ids: List[str]

    # PdfAgent Outputs
    pdf_results: List[Dict[str, Any]]

    # Analyst Outputs
    insights: List[Dict[str, str]]
    final_report: str

    # Logs for UI
    logs: Annotated[List[str], operator.add]

    # Enrichment Data
    enrichments: Dict[str, Any]
    
    # LLM Configuration
    llm_config: Dict[str, Any]  # Contains: model, temperature, top_p, frequency_penalty
