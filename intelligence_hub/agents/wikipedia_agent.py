"""
Wikipedia Enrichment Agent

Autonomous agent for extracting historical and structural information from Wikipedia.
Includes integrated Wikipedia fetching and parsing logic.
"""

import json
import re
import wikipedia
from typing import Dict, Optional, Callable, List

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


class WikipediaAgent(BaseAgent):
    """Agent for Wikipedia enrichment"""

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="Wikipedia Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )
        wikipedia.set_lang("en")

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Decide if Wikipedia enrichment should run

        Args:
            state: Shared agent state

        Returns:
            (should_run, reasoning)
        """
        basic_profile = state.get("enrichments", {})

        # Load decision prompt
        decision_prompt = load_prompt("agent_wikipedia_decision.txt")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", decision_prompt),
                (
                    "user",
                    "Analyze this company profile and decide if Wikipedia enrichment should be performed:\n\n{profile_json}",
                ),
            ]
        )

        # Invoke LLM for decision
        chain = prompt | self.llm_connector.llm
        response = chain.invoke({"profile_json": json.dumps(basic_profile, indent=2)})

        # Parse decision
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            decision = json.loads(content.strip())
            should_run = decision.get("should_execute", False)
            reasoning = decision.get(
                "reasoning",
                "No reasoning provided",
            )

            return (should_run, reasoning)

        except Exception as e:
            self.log(
                f"Decision parsing failed: {e}, defaulting to SKIP",
                "WARNING",
            )
            return (False, f"Decision error: {e}")

    def _fetch_wikipedia_data(
        self,
        company_name: str,
        wikipedia_url: str = None,
    ) -> Dict:
        """
        Fetch and parse Wikipedia data

        Args:
            company_name: Company name to search
            wikipedia_url: Optional direct Wikipedia URL

        Returns:
            Dict with Wikipedia data
        """
        result = {
            "wikipedia_url": wikipedia_url or "",
            "summary": "",
            "history": "",
            "subsidiaries": [],
            "acquisitions": [],
            "founded": "",
            "headquarters": "",
            "industry": "",
            "revenue": "",
            "employees": "",
            "error": None,
        }

        try:
            # Determine page title
            if wikipedia_url:
                page_title = self._extract_title_from_url(wikipedia_url)
            else:
                # Search for page
                search_results = wikipedia.search(company_name, results=3)
                if not search_results:
                    result["error"] = "No Wikipedia page found"
                    return result
                page_title = search_results[0]

            # Fetch the page
            self.log(f"Fetching Wikipedia page: {page_title}")
            try:
                page = wikipedia.page(page_title, auto_suggest=False)
            except wikipedia.exceptions.DisambiguationError as e:
                # Try the first option if it looks like a company
                options = [
                    opt
                    for opt in e.options
                    if "company" in opt.lower()
                    or "corporation" in opt.lower()
                    or "holdings" in opt.lower()
                ]
                if options:
                    page = wikipedia.page(options[0], auto_suggest=False)
                else:
                    raise e

            result["wikipedia_url"] = page.url
            result["summary"] = page.summary[:500]

            # Parse content
            content = page.content
            sections = self._parse_sections(content)

            # Extract history
            if "History" in sections:
                result["history"] = sections["History"][:1000]

            # Extract subsidiaries
            result["subsidiaries"] = self._extract_subsidiaries(content)

            # Extract acquisitions
            result["acquisitions"] = self._extract_acquisitions(content)

            # Extract infobox data (simple parsing)
            infobox_data = self._extract_infobox_simple(content)
            result.update(infobox_data)

            self.log("Wikipedia data fetched successfully")

        except wikipedia.exceptions.DisambiguationError as e:
            self.log(
                f"Multiple matches found: {e.options[:3]}",
                "WARNING",
            )
            result["error"] = f"Disambiguation needed: {e.options[:3]}"
        except wikipedia.exceptions.PageError:
            self.log(
                "Wikipedia page not found",
                "WARNING",
            )
            result["error"] = "Page not found"
        except Exception as e:
            self.log(
                f"Wikipedia fetch failed: {e}",
                "ERROR",
            )
            result["error"] = str(e)

        return result

    def _extract_title_from_url(self, url: str) -> str:
        """Extract page title from Wikipedia URL"""
        parts = url.split("/wiki/")
        if len(parts) > 1:
            return parts[1].replace("_", " ")
        return url

    def _parse_sections(self, content: str) -> Dict[str, str]:
        """Parse Wikipedia content into sections"""
        sections = {}
        current_section = "Intro"
        current_text = []

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("==") and line.endswith("=="):
                if current_text:
                    sections[current_section] = "\n".join(current_text)
                current_section = line.strip("= ")
                current_text = []
            else:
                if line:
                    current_text.append(line)

        if current_text:
            sections[current_section] = "\n".join(current_text)

        return sections

    def _extract_subsidiaries(self, content: str) -> List[str]:
        """Extract subsidiaries mentioned in content"""
        subsidiaries = []
        lower_content = content.lower()

        patterns = [
            r"subsidiaries[:\s]+(.*?)(?=\n\n|\Z)",
            r"divisions[:\s]+(.*?)(?=\n\n|\Z)",
            r"brands[:\s]+(.*?)(?=\n\n|\Z)",
        ]

        for pattern in patterns:
            matches = re.finditer(
                pattern,
                lower_content,
                re.IGNORECASE | re.DOTALL,
            )
            for match in matches:
                text = match.group(1)
                words = text.split()
                for word in words:
                    if word and word[0].isupper() and len(word) > 2:
                        if word not in subsidiaries and len(subsidiaries) < 20:
                            subsidiaries.append(word)

        return subsidiaries

    def _extract_acquisitions(self, content: str) -> List[Dict]:
        """Extract acquisition information"""
        acquisitions = []
        pattern = r"acquired\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:in|for)\s+(\d{4}|\$[\d,.]+(?:\s+(?:million|billion))?)"
        matches = re.finditer(pattern, content)

        for match in matches:
            acquisition = {
                "company": match.group(1),
                "detail": match.group(2),
            }
            acquisitions.append(acquisition)
            if len(acquisitions) >= 10:
                break

        return acquisitions

    def _extract_infobox_simple(self, content: str) -> Dict:
        """Simple infobox extraction using regex"""
        info = {}
        patterns = {
            "founded": r"founded[:\s]+([^\n]+)",
            "headquarters": r"headquarters[:\s]+([^\n]+)",
            "industry": r"industry[:\s]+([^\n]+)",
            "revenue": r"revenue[:\s]+([^\n]+)",
            "employees": r"employees?[:\s]+([^\n]+)",
        }

        lower_content = content.lower()
        for key, pattern in patterns.items():
            match = re.search(
                pattern,
                lower_content,
                re.IGNORECASE,
            )
            if match:
                info[key] = match.group(1).strip()[:200]

        return info

    def execute(self, state: AgentState) -> Dict:
        """
        Execute Wikipedia enrichment

        Args:
            context: Context with basic profile

        Returns:
            Result with Wikipedia data
        """
        basic_profile = state.get("enrichments", {})
        canonical_name = (
            basic_profile.get("canonical_name")
            or state.get("company_name")
            or self.company_name
            or "Unknown"
        )
        wikipedia_url = basic_profile.get("wikipedia_url")

        self.log("PROGRESS:0:Starting Wikipedia lookup")
        self.log(f"Fetching Wikipedia data for: {canonical_name}")

        try:
            self.log("PROGRESS:30:Searching Wikipedia")
            # Fetch Wikipedia data
            wikipedia_data = self._fetch_wikipedia_data(canonical_name, wikipedia_url)

            self.log("PROGRESS:70:Retrieved Wikipedia data")

            if wikipedia_data.get("error"):
                self.log(
                    f"Wikipedia enrichment failed: {wikipedia_data['error']}",
                    "WARNING",
                )
                return {
                    "data": None,
                    "document_type": "wikipedia",
                    "metadata": {"error": wikipedia_data["error"]},
                }

            # Add canonical name to data
            wikipedia_data["canonical_name"] = canonical_name

            self.log("PROGRESS:90:Processing Wikipedia content")
            self.log("Wikipedia enrichment successful")
            self.log("PROGRESS:100:Wikipedia lookup complete")
            return {
                "data": wikipedia_data,
                "document_type": "wikipedia",
                "metadata": {
                    "source": "wikipedia",
                    "has_data": bool(wikipedia_data.get("summary")),
                },
            }

        except Exception as e:
            self.log(
                f"Wikipedia execution error: {e}",
                "ERROR",
            )
            raise
