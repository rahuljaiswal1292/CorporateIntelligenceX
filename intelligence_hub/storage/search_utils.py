"""
Search Utilities for Company Lookup

Provides helper functions for search result formatting,
matching logic, and query processing.
"""

from typing import Dict, List


def format_search_results(results: Dict, threshold: float) -> List[Dict]:
    """Format ChromaDB query results into standard output format

    Args:
        results: Raw ChromaDB query results
        threshold: Similarity threshold for filtering

    Returns:
        List of formatted search results
    """
    matches = []

    if results["documents"][0]:
        for i, distance in enumerate(results["distances"][0]):
            similarity = 1 - distance  # Convert distance to similarity
            if similarity >= threshold:
                matches.append(
                    {
                        "company_name": results["metadatas"][0][i].get(
                            "company_name", ""
                        ),
                        "canonical_name": results["metadatas"][0][i].get(
                            "canonical_name", ""
                        ),
                        "similarity": similarity,
                        "metadata": results["metadatas"][0][i],
                        "document": results["documents"][0][i],
                    }
                )

    # Sort by similarity descending, then by timestamp descending (newest first)
    matches.sort(
        key=lambda x: (
            x["similarity"],
            x["metadata"].get("timestamp", ""),
        ),
        reverse=True,
    )
    return matches


def is_exact_match(
    query_lower: str,
    canonical_name: str,
    raw_names_str: str = "",
) -> bool:
    """Check if query exactly matches canonical_name or any tried_name

    Args:
        query_lower: Lowercase query string
        canonical_name: Canonical name (lowercase)
        raw_names_str: Comma-separated tried names (lowercase)

    Returns:
        True if exact match found
    """
    # Check canonical name
    if query_lower == canonical_name:
        return True

    # Check each individual tried name (raw_names)
    if raw_names_str:
        raw_names_list = [n.strip() for n in raw_names_str.split(",") if n.strip()]
        if query_lower in raw_names_list:
            return True

    return False


def is_similar_match(
    query_lower: str,
    canonical_name: str,
    raw_names_str: str = "",
    min_similarity: float = 0.8,
) -> bool:
    """Check if query is similar to canonical_name or any tried_name

    Uses simple string similarity (substring or length-based matching)

    Args:
        query_lower: Lowercase query string
        canonical_name: Canonical name (lowercase)
        raw_names_str: Comma-separated tried names (lowercase)
        min_similarity: Minimum similarity threshold (0-1)

    Returns:
        True if similar match found
    """
    # Check if query is substring of canonical name or vice versa
    if query_lower in canonical_name or canonical_name in query_lower:
        return True

    # Check each tried name
    if raw_names_str:
        raw_names_list = [n.strip() for n in raw_names_str.split(",") if n.strip()]
        for name in raw_names_list:
            if query_lower in name or name in query_lower:
                return True

    return False


def create_exact_match_result(
    metadata: Dict,
) -> Dict:
    """Create a search result for an exact match

    Args:
        metadata: Company metadata from ChromaDB

    Returns:
        Formatted search result with similarity=1.0
    """
    return {
        "company_name": metadata.get("company_name"),
        "canonical_name": metadata.get("canonical_name", ""),
        "similarity": 1.0,  # Perfect match
        "metadata": metadata,
        "document": "",
    }


def filter_suggestions_by_prefix(
    metadatas: List[Dict],
    query_lower: str,
    max_suggestions: int,
) -> List[Dict]:
    """Filter and format company suggestions based on prefix match

    Args:
        metadatas: List of company metadata from ChromaDB
        query_lower: Lowercase query string
        max_suggestions: Maximum number of suggestions to return

    Returns:
        List of suggestion dictionaries with label and value
    """
    suggestions = []
    seen = set()  # Avoid duplicates

    for meta in metadatas:
        company_name = meta.get("company_name", "")
        canonical_name = meta.get("canonical_name", "")
        ticker = meta.get("ticker", "")

        # Check if any field starts with query
        if (
            company_name.lower().startswith(query_lower)
            or canonical_name.lower().startswith(query_lower)
            or (ticker and ticker.lower().startswith(query_lower))
        ):
            # Use canonical name as primary label
            label = canonical_name if canonical_name else company_name

            # Add ticker if available
            if ticker:
                label = f"{label} ({ticker})"

            # Avoid duplicates
            if label not in seen:
                suggestions.append(
                    {
                        "label": label,
                        "value": company_name,
                        "ticker": ticker,
                        "canonical_name": canonical_name,
                    }
                )
                seen.add(label)

        if len(suggestions) >= max_suggestions:
            break

    return suggestions
