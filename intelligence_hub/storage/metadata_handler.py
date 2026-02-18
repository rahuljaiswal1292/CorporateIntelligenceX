"""
Metadata Handling for Profile Completeness

Handles completeness calculation and missing field detection.
"""

from typing import Dict


def calculate_completeness(
    profile_data: Dict,
) -> float:
    """Calculate profile completeness score

    Args:
        profile_data: Profile dictionary

    Returns:
        Completeness score between 0.0 and 1.0
    """
    required_fields = [
        "canonical_name",
        "website",
        "description",
        "industry",
        "ceo",
    ]
    completed_fields = sum(1 for field in required_fields if profile_data.get(field))
    return completed_fields / len(required_fields)


def get_missing_fields(
    profile_data: Dict,
) -> list:
    """Get list of missing required fields from a profile

    Args:
        profile_data: Profile dictionary

    Returns:
        List of missing field names
    """
    required_fields = [
        "canonical_name",
        "website",
        "description",
        "industry",
        "ceo",
        "headquarters",
        "founded",
        "employees",
        "revenue",
    ]

    missing = [field for field in required_fields if not profile_data.get(field)]

    return missing


def is_profile_complete(profile_data: Dict, threshold: float = 0.7) -> bool:
    """Check if profile meets completeness threshold

    Args:
        profile_data: Profile dictionary
        threshold: Minimum completeness score (0.0-1.0)

    Returns:
        True if profile is sufficiently complete
    """
    completeness = calculate_completeness(profile_data)
    return completeness >= threshold
