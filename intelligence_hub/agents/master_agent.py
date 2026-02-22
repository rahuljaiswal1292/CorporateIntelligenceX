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
from intelligence_hub.llm.connector import LLMConnector
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
from intelligence_hub.config.config import DATA_DIRECTORY
from intelligence_hub.prompts import load_prompt
from intelligence_hub.config.settings import config
from intelligence_hub.scrapers.adx import ADXScraper
from intelligence_hub.scrapers.dfm import DFMScraper
from intelligence_hub.connectors.web_scraper_connector import WebScraperConnector
import asyncio


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
        if profile_store and log_callback:
            log_callback("PROGRESS:2:Initializing Master Agent")

        if log_callback:
            log_callback("PROGRESS:5:Database check complete, initializing agents")

        super().__init__(
            agent_name="Master Coordination Agent",
            company_name=company_name,  # Start with raw query
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )
        self.original_query = company_name
        self.enable_enrichment = enable_enrichment
        self.llm_connector = llm_connector

        # Initialize SERP API agent (still used by master)
        self.serpapi_agent = SerpAPIProfileAgent(
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

        # Worker agents (Wikipedia, News, DED) are now workflow nodes
        # Removed from master_agent initialization - they execute as separate nodes
        # self.worker_agents = [...]

    def get_competitor_analysis(self, company_name: str) -> Dict:
        """
        Generates a competitor analysis using LLM knowledge.
        Returns top 5 UAE peers with key metrics.
        """
        self.log(f"Generating competitor analysis for {company_name}...")

        prompt = f"""
        Identify the top 5 peer competitors for '{company_name}' in the UAE market (focus on same sector/exchange).
        For each competitor, provide estimated key metrics based on your knowledge:
        1. Market Cap (in AED, e.g., '10B AED')
        2. P/E Ratio (approx)
        3. Revenue Growth YoY (approx %)

        Return strict JSON format with a single key 'peers', which is a list of objects.
        Each object must have these exact keys:
        - "Company": str
        - "market_cap": str
        - "pe_ratio": str
        - "revenue_growth": str

        Example:
        {{
          "peers": [
            {{
              "Company": "Competitor X",
              "market_cap": "15B AED",
              "pe_ratio": "12.5",
              "revenue_growth": "5%"
            }}
          ]
        }}
        """

        try:
            response = self.llm_connector.analyze(prompt)
            # clean markdown
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_resp)
            return data
        except Exception as e:
            self.log(f"Competitor analysis failed: {e}", "ERROR")
            return {"peers": []}

    def get_competitor_analysis(self, company_name: str) -> Dict:
        """
        Generates a competitor analysis using LLM knowledge.
        Returns top 5 UAE peers with key metrics.
        """
        self.log(f"Generating competitor analysis for {company_name}...")

        prompt = f"""
        Identify the top 5 peer competitors for '{company_name}' in the UAE market (focus on same sector/exchange).
        For each competitor, provide estimated key metrics based on your knowledge:
        1. Market Cap (in AED, e.g., '10B AED')
        2. P/E Ratio (approx)
        3. Revenue Growth YoY (approx %)

        Return strict JSON format with a single key 'peers', which is a list of objects.
        Each object must have these exact keys:
        - "Company": str
        - "market_cap": str
        - "pe_ratio": str
        - "revenue_growth": str

        Example:
        {{
          "peers": [
            {{
              "Company": "Competitor X",
              "market_cap": "15B AED",
              "pe_ratio": "12.5",
              "revenue_growth": "5%"
            }}
          ]
        }}
        """

        try:
            response = self.llm_connector.analyze(prompt)
            # clean markdown
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_resp)
            return data
        except Exception as e:
            self.log(f"Competitor analysis failed: {e}", "ERROR")
            return {"peers": []}

    def resolve_query(self, query: str) -> Dict[str, str]:
        """Phase 0: Entity Resolution"""
        self.log(f"PHASE 0: Resolving entity for query: '{query}'")
        query_lower = query.lower()

        # 1. Config Check
        for key, val in config.KNOWN_TICKER_MAP.items():
            if key in query_lower:
                self.log(f"Resolved via Config: {val['name']}")
                return {
                    "ticker": val["ticker"],
                    "exchange": val["exchange"],
                    "company_name": val["name"],
                    "website": val.get("website", ""),
                }

        # 2. ChromaDB Check (Semantic)
        if self.profile_store:
            matches = self.profile_store.find_similar_company(query, max_results=1)
            if matches and len(matches) > 0:
                top_match = matches[0]
                if top_match["distance"] < 0.4:  # Specific threshold
                    meta = top_match["metadata"]
                    self.log(f"Resolved via DB: {meta.get('canonical_name')}")
                    return {
                        "ticker": meta.get("ticker", ""),
                        "exchange": meta.get("exchange", ""),
                        "company_name": meta.get("canonical_name"),
                        "website": meta.get("website", ""),
                    }

        # 3. Dynamic Search (Fallback)
        self.log("Starting dynamic resolution via scrapers...")

        sb_connector = WebScraperConnector()
        adx_scanner = ADXScraper(sb_connector)
        dfm_scanner = DFMScraper(sb_connector)

        def safe_run_async(coro):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio

                    nest_asyncio.apply()
                    return loop.run_until_complete(coro)
                else:
                    return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)

        found_ticker = None
        found_exchange = None
        found_name = None

        try:
            # Try ADX
            _t, _n = safe_run_async(adx_scanner.search_ticker(query))
            if _t:
                found_ticker = _t
                found_name = _n
                found_exchange = "ADX"
        except Exception:
            pass

        if not found_ticker:
            try:
                # Try DFM
                _t, _n = safe_run_async(dfm_scanner.search_ticker(query))
                if _t:
                    found_ticker = _t
                    found_name = _n
                    found_exchange = "DFM"
            except Exception:
                pass

        if found_ticker:
            self.log(f"Resolved via Dynamic Search: {found_name}")
            # Cache it? profile_store.store_company_profile(...) - Maybe later in workflow
            return {
                "ticker": found_ticker,
                "exchange": found_exchange,
                "company_name": found_name,
                "website": "",
            }

        self.log(f"Could not resolve '{query}'. Proceeding with raw query.")
        return {
            "ticker": "UNKNOWN",
            "company_name": query.title(),
            "exchange": "UNKNOWN",
            "website": "",
        }

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
            self.data_dir = Path(DATA_DIRECTORY) / self._sanitize_company_name(
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

        # Phase 0: Resolution
        resolution = self.resolve_query(
            self.company_name
        )  # self.company_name is raw query here
        self.company_name = resolution[
            "company_name"
        ]  # Update to canonical/resolved name
        self.log(f"Target Company: {self.company_name}")

        # Update state with resolution info
        # Note: 'state' is a dict, we can't easily update it in place if it's not returned?
        # But 'execute' returns a dict. The 'run' method (wrapper) merges it.
        # Wait, 'execute' returns 'final_profile'.
        # We need to ensure 'resolution' data gets into the state.
        # But 'MasterAgent' returns dict which merges into state?
        # Typically MasterAgent is used to Generate 'enrichments'.

        # We should continue with research based on resolved name.

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
            self.data_dir = Path(DATA_DIRECTORY) / self._sanitize_company_name(
                canonical_name
            )
            self.log(f"Confirmed canonical name for enrichment: {canonical_name}")

        # Phase 2: Enrichment now handled by workflow nodes (Wikipedia, News, DED)
        # Removed: enrichment_results = self.run_enrichment_phase(basic_profile)
        self.log(
            "PROGRESS:40:Phase 2 - Child agents (Wikipedia, News, DED) running as workflow nodes"
        )
        self.log("Note: Enrichment agents now execute as separate workflow nodes")

        enrichment_results = []

        # New: Competitor Analysis
        if self.enable_enrichment:
            self.log("PROGRESS:70:Running Competitor Analysis")
            competitor_data = self.get_competitor_analysis(self.company_name)
            if competitor_data and competitor_data.get("peers"):
                self.log(f"Identified {len(competitor_data['peers'])} competitors")
                enrichment_results.append(
                    {
                        "agent": "Competitor Analysis",
                        "status": "completed",
                        "data": competitor_data,
                    }
                )

        # New: Competitor Analysis
        if self.enable_enrichment:
            self.log("PROGRESS:70:Running Competitor Analysis")
            competitor_data = self.get_competitor_analysis(self.company_name)
            if competitor_data and competitor_data.get("peers"):
                self.log(f"Identified {len(competitor_data['peers'])} competitors")
                enrichment_results.append(
                    {
                        "agent": "Competitor Analysis",
                        "status": "completed",
                        "data": competitor_data,
                    }
                )

        # Phase 3: Aggregate Results
        self.log("PROGRESS:80:Phase 3 - Aggregating results")
        final_profile = self.aggregate_results(basic_profile, enrichment_results)

        # Save basic profile to ChromaDB
        self.log("Storing basic profile to ChromaDB...")
        stored = self.save_to_chromadb(
            basic_profile,
            "basic_profile",
        )

        if stored:
            self.log(
                "Basic profile stored in ChromaDB",
                "SUCCESS",
            )
        else:
            self.log(
                "Failed to store basic profile in ChromaDB",
                "WARNING",
            )

        self.log("PROGRESS:100:Master agent workflow complete")

        # === FINAL OUTPUT LOGGING ===
        self.log("")
        self.log("=" * 70)
        self.log("MASTER AGENT FINAL OUTPUT")
        self.log("=" * 70)
        self.log(f"Original Query: {self.original_query}")
        self.log(f"Canonical Name: {basic_profile.get('canonical_name', 'N/A')}")
        self.log(f"Confidence Score: {basic_profile.get('confidence_score', 0)}%")
        self.log(f"Ticker: {resolution.get('ticker', 'N/A')}")
        self.log(f"Exchange: {resolution.get('exchange', 'N/A')}")
        self.log(f"Website: {resolution.get('website', 'N/A')}")
        self.log(
            f"Has Knowledge Panel: {basic_profile.get('has_knowledge_panel', False)}"
        )
        self.log(
            f"Has Official Website: {basic_profile.get('has_official_website', False)}"
        )
        self.log(f"Stored in ChromaDB: {stored}")
        self.log(f"Timestamp: {datetime.now().isoformat()}")

        # Log SERP links used for enrichment
        serp_links = basic_profile.get("serp_links", [])
        if serp_links:
            self.log("")
            self.log("SERP Links Used for Enrichment:")
            for idx, link in enumerate(serp_links[:10], 1):  # Show first 10 links
                link_url = link.get("link", "N/A") if isinstance(link, dict) else link
                link_title = (
                    link.get("title", "Untitled") if isinstance(link, dict) else "Link"
                )
                self.log(f"  {idx}. {link_title}")
                self.log(f"     URL: {link_url}")
            if len(serp_links) > 10:
                self.log(f"  ... and {len(serp_links) - 10} more links")

        # Log knowledge panel info if available
        if basic_profile.get("has_knowledge_panel"):
            self.log("")
            self.log("Knowledge Panel Data:")
            kg_data = basic_profile.get("knowledge_graph", {})
            if kg_data.get("description"):
                self.log(f"  Description: {kg_data.get('description')[:100]}...")
            if kg_data.get("type"):
                self.log(f"  Type: {kg_data.get('type')}")

        self.log("=" * 70)
        self.log("Master agent completed - child agents will execute as workflow nodes")
        self.log("=" * 70)
        self.log("")

        return {
            "data": basic_profile,
            "document_type": "basic_profile",
            "metadata": {
                "canonical_name": basic_profile.get("canonical_name", ""),
                "confidence": basic_profile.get("confidence_score", 0),
                "stored_in_chromadb": stored,
                "ticker": resolution.get("ticker"),
                "exchange": resolution.get("exchange"),
                "website": resolution.get("website"),
            },
        }
