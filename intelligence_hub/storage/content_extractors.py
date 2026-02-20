"""
Content Extraction for Profile Text Generation

Handles extraction of text content for embeddings.
"""

from typing import Dict


def create_name_text(profile_data: Dict, company_name: str) -> str:
    """Create concise text for name matching - only essential identifiers

    Args:
        profile_data: Company profile dictionary
        company_name: Company name

    Returns:
        Text optimized for name/ticker matching
    """
    text_parts = []

    # Company names (repeated for weight)
    canonical = profile_data.get("canonical_name", "")
    if canonical:
        text_parts.extend([canonical] * 15)
    else:
        text_parts.extend([company_name] * 15)

    if company_name and company_name != canonical:
        text_parts.extend([company_name] * 15)

    # Ticker symbol (very important for matching)
    ticker = profile_data.get("ticker", "")
    if ticker:
        text_parts.extend([ticker] * 10)

    # Industry (helps differentiate companies with similar names)
    industry = profile_data.get("industry", "")
    if industry:
        text_parts.append(industry)

    # Key people (optional, for matching)
    ceo = profile_data.get("ceo", "")
    if ceo:
        text_parts.append(ceo)

    return " ".join(text_parts)


def create_details_text(
    profile_data: Dict,
) -> str:
    """Create comprehensive text for detailed profile with all information

    Args:
        profile_data: Company profile dictionary

    Returns:
        Text containing all profile fields for semantic search
    """
    text_parts = []

    # Add all profile fields for semantic search on details
    for key, value in profile_data.items():
        if value and key not in [
            "timestamp",
            "profile_id",
        ]:
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, (int, float)):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                for (
                    sub_key,
                    sub_value,
                ) in value.items():
                    text_parts.append(f"{key}_{sub_key}: {sub_value}")
            elif isinstance(value, list):
                text_parts.append(f"{key}: {', '.join(map(str, value))}")

    return " | ".join(text_parts)


def create_profile_text(
    profile_data: Dict,
) -> str:
    """Legacy method - now calls create_name_text for backward compatibility

    Args:
        profile_data: Company profile dictionary

    Returns:
        Text for profile embedding
    """
    company_name = profile_data.get(
        "company_name",
        profile_data.get("canonical_name", ""),
    )
    return create_name_text(profile_data, company_name)
