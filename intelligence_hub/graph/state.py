from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph.message import add_messages


def replace(old, new):
    return new


def merge_dicts(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, typically for enrichments"""
    if old is None:
        return new or {}
    updated = dict(old)
    if new:
        updated.update(new)
    return updated


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
    final_report: Annotated[Any, replace]

    # Logs for UI
    logs: Annotated[List[str], operator.add]

    # Enrichment Data
    enrichments: Annotated[Dict[str, Any], merge_dicts]

    # LLM Configuration
    llm_config: Annotated[
        Dict[str, Any], replace
    ]  # Contains: model, temperature, top_p, frequency_penalty

    # Presentation/UI Outputs
    meta: Annotated[Dict[str, Any], replace]
    financials: Annotated[Dict[str, Any], replace]
    competitors: Annotated[List[Dict[str, Any]], replace]
    risks: Annotated[List[Dict[str, Any]], replace]
    chart: Annotated[Dict[str, Any], replace]
    sources: Annotated[List[Dict[str, Any]], replace]
