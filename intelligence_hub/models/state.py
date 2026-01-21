"""State models and data classes"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class InvestigationState:
    """Investigation workflow state"""

    user_input: str = ""
    canonical_name: str = ""
    ticker: str = ""
    exchange: str = ""
    profile_data: Dict[str, Any] = field(default_factory=dict)
    financial_data: Dict[str, Any] = field(default_factory=dict)
    governance_data: Dict[str, Any] = field(default_factory=dict)
    risk_insights: List[str] = field(default_factory=list)
    strategic_takeaways: List[str] = field(default_factory=list)
    progress: int = 0
    logs: List[str] = field(default_factory=list)
    cache_hit: bool = False
    started_at: float = field(default_factory=lambda: __import__('time').time())
    completed_at: Optional[float] = None

@dataclass
class CompanyIdentity:
    """Resolved company identity"""

    canonical_name: str
    ticker: str
    exchange: str
    confidence: str
    reasoning: str
    resolved_at: float = field(default_factory=lambda: __import__('time').time())

@dataclass
class CachedData:
    """Cached company data"""

    profile: Dict[str, Any]
    financials: Dict[str, Any]
    governance: Dict[str, Any]
    insights: List[str]
    risks: List[str]
    last_market_update: float
    cached_at: float = field(default_factory=lambda: __import__('time').time())