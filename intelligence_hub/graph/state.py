from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph.message import add_messages


def replace(old, new):
    return new


class AgentState(TypedDict):
    """
    Shared state object for the Intelligence Graph.
    """

    # Inputs
    query: str

    # Resolver Outputs
    ticker: Annotated[str, replace]
    company_name: Annotated[str, replace]
    canonical_name: Annotated[str, replace]  # Added for UI consistency
    exchange: Annotated[str, replace]  # ADX, DFM, or UNKNOWN
    website: Annotated[str, replace]

    # Scraper Outputs
    financial_data: Annotated[Dict[str, Any], replace]  # Structured financials
    raw_html: Annotated[str, replace]
    doc_urls: Annotated[List[str], replace]

    # Vectorizer Outputs
    vector_ids: Annotated[List[str], replace]

    # PdfAgent Outputs
    pdf_results: Annotated[List[Dict[str, Any]], replace]

    # Analyst Outputs
    insights: Annotated[List[Dict[str, str]], replace]
    final_report: Annotated[str, replace]

    # Logs for UI
    logs: Annotated[List[str], operator.add]

    # Enrichment Data
    enrichments: Annotated[Dict[str, Any], replace]

    # LLM Configuration
    llm_config: Annotated[
        Dict[str, Any], replace
    ]  # Contains: model, temperature, top_p, frequency_penalty
