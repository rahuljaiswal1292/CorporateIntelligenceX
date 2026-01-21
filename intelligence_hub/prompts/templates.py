"""LLM prompt templates"""
from langchain_core.prompts import PromptTemplate

IDENTITY_RESOLUTION_PROMPT = PromptTemplate(
    template="""You are a financial analyst specializing in UAE markets. Resolve company names/tickers to canonical forms.

User Input: {user_input}
DFM Data: {dfm_data}
ADX Data: {adx_data}

Return JSON:
{{"canonical_name": "...", "ticker": "...", "exchange": "DFM/ADX", "confidence": "high/medium/low", "reasoning": "..."}}
If no match: {{"canonical_name": null, "ticker": null, "exchange": null, "confidence": "low", "reasoning": "No match found"}}
""",
    input_variables=["user_input", "dfm_data", "adx_data"]
)

FINANCIAL_SYNTHESIS_PROMPT = """You are a senior relationship manager analyzing {canonical_name} ({ticker}) on {exchange}.

Profile: {profile_data}
Financials: {financial_data}
Governance: {governance_data}

Provide JSON:
{{"strategic_takeaways": [...], "risk_flags": [...]}}

Include 5 strategic insights and 3 risk flags.
"""

RISK_ASSESSMENT_PROMPT = PromptTemplate(
    template="""Analyze {canonical_name} for key risks.

Financials: {financial_data}
Governance: {governance_data}

Return: [{{"category": "...", "description": "...", "severity": "High/Medium/Low"}}]
""",
    input_variables=["canonical_name", "financial_data", "governance_data"]
)