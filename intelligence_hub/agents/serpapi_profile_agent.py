"""
SERP API Profile Agent

Specialized agent for extracting company profiles from SERP API data.
This is the foundational agent that establishes the canonical name and basic profile.
"""

import json
from typing import Dict, Optional, Callable
from serpapi import GoogleSearch

from intelligence_hub.config.config import SERPAPI_API_KEY
from .base_agent import BaseAgent
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.storage.corporate_profile_store import (
    CorporateProfileStore,
)
from intelligence_hub.prompts import load_prompt
from langchain_core.prompts import (
    ChatPromptTemplate,
)


class SerpAPIProfileAgent(BaseAgent):
    """Agent for SERP API profile extraction"""

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="SERP API Profile Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        SERP API agent always executes as it provides the foundational profile

        Args:
            context: Execution context (not used for this agent)

        Returns:
            (True, reasoning)
        """
        return (
            True,
            "SERP API agent must execute to establish canonical name and basic profile",
        )

    def fetch_serp_data(self, query: str) -> Dict:
        """
        Fetch raw SERP data from Google

        Args:
            query: Search query

        Returns:
            Raw SERP API response
        """
        self.log(f"Fetching SERP data for query: {query}")

        try:
            # Format query with quotes and "company" suffix for better results
            formatted_query = f'"{query}" company'

            search = GoogleSearch(
                {
                    "q": formatted_query,
                    "api_key": SERPAPI_API_KEY,
                    "engine": "google",
                    "google_domain": "google.com",
                    "hl": "en",
                    "gl": "ae",
                    "num": 10,
                    "device": "desktop",
                }
            )

            result = search.get_dict()
            self.log(f"SERP API call completed")

            # Save raw SERP data immediately
            self.save_to_disk(result, "serp_raw.json")

            return result

        except Exception as e:
            self.log(f"SERP API error: {e}", "ERROR")
            raise

    def _truncate_serp_data(
        self,
        serp_data: Dict,
        max_chars: int = 20000,
    ) -> Dict:
        """
        Intelligently truncate SERP data to stay within token limits.
        Priority: knowledge_graph > organic_results > related_questions > other

        Args:
            serp_data: Raw SERP API response
            max_chars: Maximum characters to keep (roughly 0.25 tokens per char)

        Returns:
            Truncated SERP data dictionary
        """
        truncated = {}
        current_size = 0

        # Priority 1: Knowledge graph (most important - company overview)
        if "knowledge_graph" in serp_data:
            kg = serp_data["knowledge_graph"]
            kg_json = json.dumps(kg, indent=2)
            if len(kg_json) < max_chars * 0.4:  # Allow 40% for KG
                truncated["knowledge_graph"] = kg
                current_size += len(kg_json)
                self.log(f"Included knowledge_graph ({len(kg_json)} chars)")

        # Priority 2: Organic results (top results only)
        if "organic_results" in serp_data and current_size < max_chars:
            remaining = max_chars - current_size
            results = serp_data["organic_results"][:10]  # Top 10 only

            # Truncate long snippets
            truncated_results = []
            for result in results:
                if current_size >= max_chars * 0.9:  # Stop at 90%
                    break

                truncated_result = {
                    "title": result.get("title", "")[:200],
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", "")[:300],
                }
                result_json = json.dumps(truncated_result)
                if current_size + len(result_json) < max_chars * 0.9:
                    truncated_results.append(truncated_result)
                    current_size += len(result_json)

            if truncated_results:
                truncated["organic_results"] = truncated_results
                self.log(f"Included {len(truncated_results)} organic results")

        # Priority 3: Related questions (if space remains)
        if "related_questions" in serp_data and current_size < max_chars * 0.8:
            questions = serp_data["related_questions"][:5]  # Top 5 only
            truncated_questions = []

            for q in questions:
                if current_size >= max_chars * 0.95:
                    break
                q_truncated = {
                    "question": q.get("question", "")[:200],
                    "snippet": q.get("snippet", "")[:200],
                }
                q_json = json.dumps(q_truncated)
                if current_size + len(q_json) < max_chars * 0.95:
                    truncated_questions.append(q_truncated)
                    current_size += len(q_json)

            if truncated_questions:
                truncated["related_questions"] = truncated_questions
                self.log(f"Included {len(truncated_questions)} related questions")

        # Add search metadata (small)
        if "search_metadata" in serp_data:
            truncated["search_metadata"] = {
                "query": serp_data["search_metadata"].get("query", ""),
                "status": serp_data["search_metadata"].get("status", ""),
            }

        final_json = json.dumps(truncated, indent=2)
        self.log(
            f"Truncated SERP data from ~{len(json.dumps(serp_data))} to {len(final_json)} chars"
        )

        return truncated

    def suggest_name_variations(
        self, original_query: str, serp_data: Dict
    ) -> list[str]:
        """
        Use LLM to suggest company name variations based on SERP response

        Args:
            original_query: Original company name query
            serp_data: SERP API response

        Returns:
            List of suggested name variations
        """
        self.log("Analyzing SERP data for name suggestions...")

        # Extract potential company names from SERP data
        suggestions_context = {
            "query": original_query,
            "knowledge_graph_title": serp_data.get("knowledge_graph", {}).get(
                "title", ""
            ),
            "organic_titles": [
                r.get("title", "") for r in serp_data.get("organic_results", [])[:5]
            ],
            "related_searches": [
                r.get("query", "") for r in serp_data.get("related_searches", [])[:5]
            ],
        }

        # Load prompt from file
        system_prompt = load_prompt("company_name_variations.txt")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "user",
                    "Original query: {query}\n\nSERP data: {context}\n\nSuggest 2-3 name variations:",
                ),
            ]
        )

        try:
            chain = prompt | self.llm_connector.llm
            response = chain.invoke(
                {
                    "query": original_query,
                    "context": json.dumps(
                        suggestions_context,
                        indent=2,
                    ),
                }
            )

            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            variations = json.loads(content.strip())
            self.log(f"Suggested variations: {variations}")
            return variations if isinstance(variations, list) else []

        except Exception as e:
            self.log(
                f"Failed to get name variations: {e}",
                "WARNING",
            )
            # Fallback: simple variations
            return [
                f"{original_query} LLC",
                f"{original_query} Inc",
            ]

    def analyze_serp_data(self, serp_data: Dict) -> Dict:
        """
        Use LLM to analyze SERP data and extract profile

        Args:
            serp_data: Raw SERP API response

        Returns:
            Extracted profile with metadata
        """
        self.log("Analyzing SERP data with LLM")

        # Load prompt
        system_prompt = load_prompt("agent_serpapi_profile_system.txt")

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "user",
                    "Analyze this SERP API response and extract the company profile:\n\n{serp_json}",
                ),
            ]
        )

        # Prepare SERP data with smart truncation
        # Prioritize: knowledge_graph > organic_results > related_questions > other
        truncated_data = self._truncate_serp_data(serp_data, max_chars=20000)
        serp_json = json.dumps(truncated_data, indent=2)

        # Safety check for token limit
        # Rough estimate: 4 chars ≈ 1 token, keep under 6000 tokens for safety (system prompt uses ~2000)
        if len(serp_json) > 24000:
            self.log(
                f"SERP data still large ({len(serp_json)} chars), applying additional truncation",
                "WARNING",
            )
            serp_json = serp_json[:24000] + "\n... (truncated for token limit)"

        # Invoke LLM
        chain = prompt | self.llm_connector.llm
        response = chain.invoke({"serp_json": serp_json})

        # Parse response
        try:
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            profile = json.loads(content.strip())

            self.log(
                f"Extracted profile for: {profile.get('canonical_name', 'Unknown')}"
            )
            self.log(f"Confidence score: {profile.get('confidence_score', 0)}")

            return profile

        except json.JSONDecodeError as e:
            self.log(
                f"Failed to parse LLM response: {e}",
                "ERROR",
            )
            self.log(
                f"LLM response: {response.content}",
                "ERROR",
            )
            raise

    def execute(self, state: AgentState) -> Dict:
        """
        Execute SERP API profile extraction with retry logic

        Args:
            context: Execution context (may contain initial_query)

        Returns:
            Result with profile data
        """
        self.log("PROGRESS:0:Starting SERP profile extraction")

        # Step 1: Fetch SERP data
        query = state.get("query", self.company_name)

        max_attempts = 3
        attempt = 1
        profile = None
        tried_queries = []

        while attempt <= max_attempts and not profile:
            if attempt == 1:
                search_query = query
                self.log(
                    f"Attempt {attempt}/{max_attempts}: Searching for '{search_query}'"
                )
            else:
                # Get name variations from previous SERP response
                self.log(
                    f"Canonical name not found. Attempt {attempt}/{max_attempts}: Generating name variations..."
                )
                variations = self.suggest_name_variations(query, serp_data)

                # Filter out already tried queries
                available_variations = [v for v in variations if v not in tried_queries]
                if not available_variations:
                    self.log(
                        "No more variations to try",
                        "WARNING",
                    )
                    break

                search_query = available_variations[0]
                self.log(f"Trying variation: '{search_query}'")

            tried_queries.append(search_query)

            self.log(
                f"PROGRESS:{20 + (attempt-1)*25}:Querying Google Search (attempt {attempt})"
            )
            serp_data = self.fetch_serp_data(search_query)

            self.log("PROGRESS:50:Retrieved SERP data")

            # Step 2: Analyze with LLM
            self.log("PROGRESS:60:AI analyzing search results")
            temp_profile = self.analyze_serp_data(serp_data)

            # Check if we found a canonical name
            if temp_profile.get("canonical_name") or temp_profile.get("company_name"):
                canonical = temp_profile.get("canonical_name") or temp_profile.get(
                    "company_name"
                )
                self.log(f"✓ Resolved canonical name: '{canonical}'")
                # Emit special message for UI
                self.log(f"CANONICAL_NAME_RESOLVED:{canonical}")
                profile = temp_profile
                break
            else:
                self.log(
                    f"No canonical name found in attempt {attempt}",
                    "WARNING",
                )
                attempt += 1

        # If still no profile after all attempts, use the last one
        if not profile:
            self.log(
                "Using last attempt's profile despite missing canonical name",
                "WARNING",
            )
            profile = temp_profile if "temp_profile" in locals() else {}
            self.log("CANONICAL_NAME_RESOLVED:Unknown Company")

        self.log("PROGRESS:80:Generated company profile")

        # Step 3: Add metadata
        profile["_metadata"] = {
            "agent": self.agent_name,
            "search_query": query,
            "tried_queries": tried_queries,
            "serp_api_calls": len(tried_queries),
            "attempts_needed": (attempt if profile else max_attempts),
            "extraction_timestamp": self.log.__self__.__class__.__name__,
        }

        # Step 4: Store in ChromaDB
        if self.profile_store and profile.get("confidence_score", 0) >= 50:
            canonical_name = profile.get(
                "canonical_name",
                self.company_name,
            )
            self.log("PROGRESS:90:Storing profile in ChromaDB")
            self.log(f"Storing basic profile in ChromaDB")

            self.profile_store.store_company_profile(
                company_name=canonical_name,
                profile_data=profile,
                search_query=query,
                document_type="basic_profile",
            )

        self.log("PROGRESS:100:SERP profile extraction complete")

        return {
            "data": profile,
            "document_type": "basic_profile",
            "metadata": {
                "confidence": profile.get("confidence_score", 0),
                "canonical_name": profile.get("canonical_name", ""),
                "has_knowledge_panel": profile.get("has_knowledge_panel", False),
            },
        }
