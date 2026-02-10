"""
Master Coordination Agent

Orchestrates the multi-agent research workflow:
1. Runs SERP API Profile Agent first to establish canonical name
2. Evaluates basic profile quality
3. Launches worker agents in parallel based on context
4. Aggregates results into final comprehensive profile
"""

import json
from typing import Dict, Optional, Callable, List
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from .serpapi_profile_agent import (
    SerpAPIProfileAgent,
)
from .wikipedia_agent import (
    WikipediaAgent,
)
from .news_agent import NewsAgent
from .ded_agent import DEDAgent
from intelligence_hub.storage.corporate_profile_store import (
    CorporateProfileStore,
)
from intelligence_hub.prompts import load_prompt


class MasterAgent(BaseAgent):
    """Master coordination agent for multi-agent workflow"""

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
        enable_enrichment: bool = True,
    ):
        # Check if we have a similar company in ChromaDB first
        resolved_name = company_name
        found_match = False

        if profile_store and log_callback:
            log_callback("PROGRESS:2:Checking database for existing profiles")

        if profile_store:
            try:
                # Use semantic similarity search
                matches = profile_store.find_similar_company(
                    company_name, max_results=1
                )
                if matches and len(matches) > 0:
                    # Check if it's a close match (distance < 0.6 means similar enough)
                    # ChromaDB uses cosine distance: 0 = identical, 2 = opposite
                    top_match = matches[0]
                    distance = top_match.get("distance", 1.0)
                    if distance < 0.6:  # Reasonable similarity threshold
                        resolved_name = top_match.get(
                            "canonical_name",
                            company_name,
                        )
                        found_match = True
                        if log_callback and resolved_name != company_name:
                            similarity_pct = max(
                                0,
                                (1 - distance) * 100,
                            )
                            log_callback(
                                f"🔍 Found similar company in database: '{resolved_name}' (match: {similarity_pct:.1f}%)\n"
                            )

                # Log if no match was found
                if not found_match and log_callback:
                    log_callback(
                        f"ℹ️ No existing profile found for '{company_name}' - starting new research\n"
                    )

            except Exception as e:
                if log_callback:
                    log_callback(f"⚠️ Similarity check failed: {e}\n")

        if log_callback:
            log_callback("PROGRESS:5:Database check complete, initializing agents")

        super().__init__(
            agent_name="Master Coordination Agent",
            company_name=resolved_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )
        self.original_query = company_name
        self.enable_enrichment = enable_enrichment
        self.llm_connector = llm_connector

        # Initialize worker agents
        self.serpapi_agent = SerpAPIProfileAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

        self.worker_agents = [
            WikipediaAgent(
                company_name=company_name,
                llm_connector=llm_connector,
                log_callback=log_callback,
                profile_store=profile_store,
            ),
            NewsAgent(
                company_name=company_name,
                llm_connector=llm_connector,
                log_callback=log_callback,
                profile_store=profile_store,
            ),
            DEDAgent(
                company_name=company_name,
                llm_connector=llm_connector,
                log_callback=log_callback,
                profile_store=profile_store,
            ),
        ]

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Master agent always executes

        Args:
            state: Shared agent state

        Returns:
            (True, reasoning)
        """
        return (
            True,
            "Master agent coordinates all research workflow",
        )

    def run_serpapi_phase(self, state: AgentState) -> Dict:
        """
        Phase 1: Run SERP API Profile Agent to establish canonical name

        Args:
            state: Shared agent state

        Returns:
            Basic profile result
        """
        self.log("=" * 60)
        self.log("PHASE 1: SERP API Profile Extraction")
        self.log("=" * 60)

        # Check if recent profile exists in ChromaDB
        self.log("Checking for existing profile in ChromaDB...")
        existing_profile = self.check_existing_profile(
            document_type="basic_profile",
            max_age_days=30,  # Consider profiles less than 30 days old as recent
        )

        if existing_profile:
            self.log(
                f"Found existing profile in ChromaDB",
                "SUCCESS",
            )
            canonical_name = existing_profile.get(
                "canonical_name",
                self.company_name,
            )
            confidence = existing_profile.get("confidence_score", 0)
            self.log(
                f"Using cached profile: {canonical_name} (confidence: {confidence})"
            )
            self.log("Skipping SERP API fetch to save API calls")

            return {
                "agent": "SerpAPI Profile Agent",
                "status": "completed",
                "data": existing_profile,
                "from_cache": True,
            }

        # No recent profile found, run SERP API agent
        self.log("No recent profile found, fetching from SERP API...")
        result = self.serpapi_agent.run(state)

        if result["status"] != "completed":
            self.log(
                f"SERP API extraction failed: {result.get('error')}",
                "ERROR",
            )
            return result

        # Extract basic profile
        basic_profile = result.get("data", {})
        confidence = basic_profile.get("confidence_score", 0)
        canonical_name = basic_profile.get("canonical_name", self.company_name)

        self.log(f"Basic profile extracted")
        self.log(f"Canonical Name: {canonical_name}")
        self.log(f"Confidence Score: {confidence}")
        self.log(
            f"Has Knowledge Panel: {basic_profile.get('has_knowledge_panel', False)}"
        )
        self.log(
            f"Has Official Website: {basic_profile.get('has_official_website', False)}"
        )

        # Update data directory to use canonical name immediately
        if canonical_name and canonical_name != self.company_name:
            old_dir = self.data_dir
            self.data_dir = Path("intelligence_hub/data") / self._sanitize_company_name(
                canonical_name
            )
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"Updated data directory to use canonical name: {canonical_name}")

            # Move any existing files from old directory to new directory
            if old_dir.exists() and old_dir != self.data_dir:
                import shutil

                for item in old_dir.iterdir():
                    dest = self.data_dir / item.name
                    if item.is_file():
                        shutil.move(str(item), str(dest))
                        self.log(f"Moved {item.name} to canonical directory")
                # Try to remove old directory if empty
                try:
                    old_dir.rmdir()
                except:
                    pass  # Directory not empty or other error, ignore

            # Update serpapi_agent's data_dir too
            self.serpapi_agent.data_dir = self.data_dir

        return result

    def run_enrichment_phase(self, basic_profile: Dict) -> List[Dict]:
        """
        Phase 2: Run worker agents in parallel for enrichment

        Args:
            basic_profile: Basic profile from SERP API

        Returns:
            List of enrichment results
        """
        if not self.enable_enrichment:
            self.log("Enrichment disabled, skipping Phase 2")
            return []

        self.log("")
        self.log("=" * 60)
        self.log("PHASE 2: Parallel Enrichment Agents")
        self.log("=" * 60)

        # Prepare context for worker agents
        state_for_workers = {
            "enrichments": basic_profile,
            "company_name": basic_profile.get("canonical_name", self.company_name),
        }

        # Run agents in parallel
        results = []

        with ThreadPoolExecutor(max_workers=len(self.worker_agents)) as executor:
            # Submit all agent tasks
            future_to_agent = {
                executor.submit(agent.run, state_for_workers): agent
                for agent in self.worker_agents
            }

            # Collect results as they complete
            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    result = future.result()
                    results.append(result)

                    self.log(
                        f"{agent.agent_name} completed with status: {result['status']}"
                    )

                except Exception as e:
                    self.log(
                        f"{agent.agent_name} raised exception: {e}",
                        "ERROR",
                    )
                    results.append(
                        {
                            "agent": agent.agent_name,
                            "status": "failed",
                            "error": str(e),
                            "data": None,
                        }
                    )

        return results

    def aggregate_results(
        self,
        basic_profile: Dict,
        enrichment_results: List[Dict],
    ) -> Dict:
        """
        Aggregate all results into final comprehensive profile

        Args:
            basic_profile: Basic profile from SERP API
            enrichment_results: Results from worker agents

        Returns:
            Final aggregated profile
        """
        self.log("")
        self.log("=" * 60)
        self.log("PHASE 3: Results Aggregation")
        self.log("=" * 60)

        # Start with basic profile
        final_profile = dict(basic_profile)

        # Add enrichment data
        enrichments = {}
        for result in enrichment_results:
            agent_name = result.get("agent", "unknown")
            status = result.get("status")

            if status == "completed" and result.get("data"):
                doc_type = result.get("data", {}).get("canonical_name")
                enrichments[agent_name] = {
                    "status": "success",
                    "data": result.get("data"),
                }
                self.log(f"Included data from {agent_name}")
            elif status == "skipped":
                enrichments[agent_name] = {
                    "status": "skipped",
                    "reasoning": result.get("reasoning"),
                }
                self.log(f"Skipped {agent_name}: {result.get('reasoning')}")
            else:
                enrichments[agent_name] = {
                    "status": "failed",
                    "error": result.get("error"),
                }
                self.log(
                    f"Failed {agent_name}: {result.get('error')}",
                    "WARNING",
                )

        final_profile["enrichments"] = enrichments
        final_profile["enrichment_timestamp"] = datetime.now().isoformat()

        # Calculate enrichment stats
        completed = sum(1 for r in enrichment_results if r.get("status") == "completed")
        skipped = sum(1 for r in enrichment_results if r.get("status") == "skipped")
        failed = sum(1 for r in enrichment_results if r.get("status") == "failed")

        self.log(
            f"Enrichment Summary: {completed} completed, {skipped} skipped, {failed} failed"
        )

        return final_profile

    def execute(self, state: AgentState) -> Dict:
        """
        Execute full multi-agent research workflow

        Args:
            state: Shared agent state

        Returns:
            Final comprehensive profile
        """
        self.log("PROGRESS:0:Starting research workflow")
        self.log("Starting multi-agent research workflow")
        self.log(f"Target Company: {self.company_name}")

        # Phase 1: SERP API Profile Extraction
        self.log("PROGRESS:10:Phase 1 - Basic profile extraction")
        serpapi_result = self.run_serpapi_phase(state)

        if serpapi_result["status"] != "completed":
            return {
                "data": None,
                "error": "Failed to extract basic profile",
                "metadata": serpapi_result,
            }

        basic_profile = serpapi_result.get("data", {})

        # Update data directory to use canonical name if available
        canonical_name = basic_profile.get("canonical_name")
        # Already updated earlier, but ensure it's set for enrichment agents
        if canonical_name and canonical_name != self.company_name:
            # Ensure data_dir is using canonical name
            self.data_dir = Path("intelligence_hub/data") / self._sanitize_company_name(
                canonical_name
            )
            self.log(f"Confirmed canonical name for enrichment: {canonical_name}")

        # Phase 2: Parallel Enrichment
        self.log("PROGRESS:40:Phase 2 - Enrichment with Wikipedia, News, DED")
        enrichment_results = self.run_enrichment_phase(basic_profile)

        # Phase 3: Aggregate Results
        self.log("PROGRESS:80:Phase 3 - Aggregating results")
        final_profile = self.aggregate_results(basic_profile, enrichment_results)

        # Save final profile to disk
        self.log("PROGRESS:90:Saving final profile")
        self.save_to_disk(final_profile, "final_profile.json")

        # Save final aggregated profile to ChromaDB
        self.log("Storing final aggregated profile to ChromaDB...")
        stored = self.save_to_chromadb(
            final_profile,
            "comprehensive_profile",
        )

        if stored:
            self.log(
                "Final profile stored in ChromaDB",
                "SUCCESS",
            )
        else:
            self.log(
                "Failed to store final profile in ChromaDB",
                "WARNING",
            )

        self.log("PROGRESS:100:Research workflow complete")
        self.log("")
        self.log("=" * 60)
        self.log("Research workflow completed successfully")
        self.log("=" * 60)

        return {
            "data": final_profile,
            "document_type": "comprehensive_profile",
            "metadata": {
                "canonical_name": final_profile.get("canonical_name", ""),
                "confidence": final_profile.get("confidence_score", 0),
                "enrichment_count": len(enrichment_results),
                "stored_in_chromadb": stored,
            },
        }
