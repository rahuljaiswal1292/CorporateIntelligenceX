"""
Shareholder Enrichment Agent

Autonomous agent for extracting shareholder and ownership structure information.
Uses LLM to distill information from available enrichments (Wikipedia, SERP, DED).
"""

import json
from typing import Dict, Optional, Callable, List
from datetime import datetime

from .base_agent import BaseAgent
from intelligence_hub.graph.state import AgentState
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import (
    CorporateProfileStore,
)
from intelligence_hub.prompts import load_prompt
from langchain_core.prompts import (
    ChatPromptTemplate,
)


class ShareholderAgent(BaseAgent):
    """Agent for shareholder and ownership structure extraction"""

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="Shareholder Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Always execute for now to ensure we have shareholder data.
        """
        return (True, "Shareholder analysis is requested for the company profile.")

    def _extract_shareholders_with_llm(
        self,
        company_name: str,
        available_data: Dict,
    ) -> Dict:
        """
        Use LLM to extract shareholder information from available data
        """
        self.log(f"Extracting shareholder information for {company_name}")
        
        # Load prompt - we'll create this or use a default if not found
        try:
            extraction_prompt = load_prompt("shareholder_extraction.txt")
        except:
            extraction_prompt = """
            You are a corporate intelligence analyst. Your task is to extract the shareholder structure and major owners of the company: {company_name}.
            
            Based on the provided data, identify:
            1. Major shareholders (individuals or entities) and their approximate percentages if available.
            2. Ownership type (Publicly listed, Government-owned, Private, Family-owned).
            3. Key directors or board members if mentioned in the context of ownership.
            4. Ultimate parent company or ultimate beneficial owner (UBO) if applicable.
            
            Provided Context Data:
            {context_data}
            
            Return the result in JSON format:
            {{
                "ownership_type": "string",
                "major_shareholders": [
                    {{
                        "name": "string",
                        "percentage": "string or null",
                        "type": "Individual/Entity/Government"
                    }}
                ],
                "ultimate_beneficial_owner": "string or null",
                "board_members": ["string"],
                "ownership_notes": "string summary"
            }}
            """

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", extraction_prompt),
                (
                    "user",
                    "Extract shareholder data for {company_name} from the following context:\n\n{context_data}",
                ),
            ]
        )

        # Prepare context data
        context_data = ""
        
        # Add Wikipedia summary if available
        wiki = available_data.get("wikipedia", {})
        if wiki and wiki.get("summary"):
            context_data += f"Wikipedia Summary: {wiki.get('summary')}\n\n"
            
        # Add DED information (partners/shareholders)
        ded = available_data.get("uae_ded_license", {})
        if ded and ded.get("data") and ded["data"].get("summary"):
            summary = ded["data"].get("summary", {})
            partners = summary.get("shareholder_details", [])
            if partners:
                context_data += f"DED Partner/Shareholder Info: {json.dumps(partners)}\n\n"
                
        # Add SERP summaries if available
        serp_profile = available_data.get("serp_profile", {})
        if serp_profile:
            context_data += f"Corporate Profile (SERP-based): {json.dumps(serp_profile)}\n\n"

        # Invoke LLM
        chain = prompt | self.llm_connector.llm
        try:
            response = chain.invoke({
                "company_name": company_name,
                "context_data": context_data if context_data else "No specific data available. Use your general knowledge."
            })
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except Exception as e:
            self.log(f"Extraction failed: {e}", "ERROR")
            return {
                "ownership_type": "Unknown",
                "major_shareholders": [],
                "ultimate_beneficial_owner": None,
                "board_members": [],
                "ownership_notes": f"Error during extraction: {str(e)}"
            }

    def execute(self, state: AgentState) -> Dict:
        """
        Execute shareholder extraction
        """
        self.log("PROGRESS:0:Starting shareholder analysis")
        
        company_name = (
            state.get("canonical_name")
            or state.get("company_name")
            or self.company_name
            or "Unknown"
        )
        
        enrichments = state.get("enrichments", {})
        
        self.log("PROGRESS:30:Analyzing available data sources")
        
        # Perform extraction
        shareholder_data = self._extract_shareholders_with_llm(company_name, enrichments)
        
        self.log(f"Extracted {len(shareholder_data.get('major_shareholders', []))} major shareholders")
        
        self.log("PROGRESS:100:Shareholder analysis complete")
        
        return {
            "data": shareholder_data,
            "document_type": "shareholder_structure",
            "metadata": {
                "source": "llm_extraction",
                "timestamp": datetime.now().isoformat(),
            },
        }
