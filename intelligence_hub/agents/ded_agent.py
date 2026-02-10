"""
UAE DED License Agent

Autonomous agent for querying Dubai DED license database.
Includes integrated ChromaDB querying logic.
"""

import json
import ast
import os
import chromadb
from datetime import datetime
from typing import Dict, Optional, Callable, List

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


class DEDAgent(BaseAgent):
    """Agent for UAE DED license lookup"""

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="DED Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

        # Initialize ChromaDB client for DED database (separate path to avoid conflicts)
        try:
            ded_db_path = os.path.join(os.getcwd(), "data", "chroma_db_ded")
            # Create directory if it doesn't exist
            os.makedirs(ded_db_path, exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(path=ded_db_path)
        except Exception as e:
            self.log(
                f"Failed to initialize DED ChromaDB client: {e}",
                "WARNING",
            )
            self.chroma_client = None

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Decide if DED lookup should run

        Args:
            state: Shared agent state

        Returns:
            (should_run, reasoning)
        """
        basic_profile = state.get("enrichments", {})

        # Load decision prompt
        decision_prompt = load_prompt("agent_ded_decision.txt")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", decision_prompt),
                (
                    "user",
                    "Analyze this company profile and decide if UAE DED license lookup should be performed:\n\n{profile_json}",
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

    def _get_serp_profile_from_chromadb(self, company_name: str) -> Optional[Dict]:
        """
        Retrieve SERP profile data from ChromaDB for comparison

        Args:
            company_name: Company name to search

        Returns:
            Dict with SERP profile data or None
        """
        if not self.profile_store:
            return None

        try:
            # Get full profile from details collection
            profile = self.profile_store.get_full_profile_from_details(company_name)

            if profile:
                self.log(f"Retrieved SERP profile for comparison")
                return {
                    "description": profile.get("description", ""),
                    "industry": profile.get("industry", ""),
                    "headquarters": profile.get("headquarters", ""),
                    "website": profile.get("website", ""),
                    "founded_year": profile.get("founded_year", ""),
                    "ceo": profile.get("ceo", ""),
                    "canonical_name": profile.get("canonical_name", ""),
                    "employees": profile.get("employees", ""),
                    "revenue": profile.get("revenue", ""),
                }
            return None
        except Exception as e:
            self.log(
                f"Failed to retrieve SERP profile: {e}",
                "WARNING",
            )
            return None

    def _query_ded_database(
        self,
        company_name: str,
        top_k: int = 10,
        similarity_threshold: float = 0.5,
    ) -> Dict:
        """
        Query DED license database via ChromaDB using hybrid approach:
        1. Exact match on canonical name
        2. Similarity search on trade names and activities

        Args:
            company_name: Company name to search
            top_k: Number of results to fetch
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Dict with license data and metadata
        """
        result = {
            "companies": [],
            "total_found": 0,
            "query": company_name,
            "search_method": "hybrid",
            "error": None,
        }

        try:
            # Get DED collection
            try:
                collection = self.chroma_client.get_collection(name="uae_ded_licenses")
            except Exception:
                self.log(
                    "DED licenses collection not found in ChromaDB",
                    "WARNING",
                )
                result["error"] = (
                    "DED database not available - run aggregate_ded_extract.py and load to ChromaDB"
                )
                return result

            self.log(f"Querying DED database for: {company_name}")
            self.log("PROGRESS:25:Initiating DED search")

            companies_dict = {}  # Use dict to avoid duplicates

            # STEP 1: Try exact match on trade_name_en (using metadata filter)
            self.log("Step 1: Trying exact match on trade name...")
            try:
                exact_results = collection.get(
                    where={"trade_name_en": {"$eq": company_name}},
                    include=[
                        "metadatas",
                        "documents",
                    ],
                )

                if exact_results["ids"]:
                    self.log(f"Found exact match!")
                    for i, metadata in enumerate(exact_results["metadatas"]):
                        company_data = self._parse_aggregated_license_data(
                            metadata,
                            similarity_score=1.0,
                            match_type="exact",
                        )
                        if company_data:
                            key = company_data["trade_name_en"]
                            companies_dict[key] = company_data
            except Exception as e:
                self.log(
                    f"Exact match query failed: {e}",
                    "WARNING",
                )

            # STEP 2: Similarity search on searchable text
            self.log(f"Step 2: Performing similarity search (top {top_k})...")
            self.log(f"Searching ChromaDB for similar companies...")
            self.log(f"This may take 10-30 seconds for large datasets...")
            try:
                import time
                import threading

                start_time = time.time()

                query_results = None
                query_error = None
                query_complete = threading.Event()

                # Run query in separate thread
                def run_query():
                    nonlocal query_results, query_error
                    try:
                        query_results = collection.query(
                            query_texts=[company_name],
                            n_results=top_k,
                            include=[
                                "metadatas",
                                "documents",
                                "distances",
                            ],
                        )
                    except Exception as e:
                        query_error = e
                    finally:
                        query_complete.set()

                query_thread = threading.Thread(target=run_query)
                query_thread.start()

                # Log progress while waiting
                wait_seconds = 0
                while not query_complete.is_set():
                    query_complete.wait(5)  # Wait 5 seconds at a time
                    if not query_complete.is_set():
                        wait_seconds += 5
                        self.log(f"Still searching... ({wait_seconds}s elapsed)")

                query_thread.join()

                if query_error:
                    raise query_error

                elapsed = time.time() - start_time
                self.log(
                    f"ChromaDB search completed in {elapsed:.2f}s, processing results..."
                )

                if query_results["ids"] and query_results["ids"][0]:
                    self.log("PROGRESS:35:Processing similarity matches")
                    total_results = len(query_results["metadatas"][0])
                    self.log(f"Processing {total_results} results from ChromaDB...")

                    processed = 0
                    for i, metadata in enumerate(query_results["metadatas"][0]):
                        # Log progress every 25%
                        if (
                            total_results > 4
                            and i % (total_results // 4) == 0
                            and i > 0
                        ):
                            self.log(f"Processed {i}/{total_results} results...")

                        # Calculate similarity score (convert distance to similarity)
                        distance = query_results["distances"][0][i]
                        similarity = 1 - distance

                        # Filter by threshold
                        if similarity < similarity_threshold:
                            continue

                        # Parse aggregated license data
                        company_data = self._parse_aggregated_license_data(
                            metadata,
                            similarity_score=similarity,
                            match_type="similarity",
                        )

                        if company_data:
                            key = company_data["trade_name_en"]
                            # Keep the one with higher similarity if duplicate
                            if (
                                key not in companies_dict
                                or companies_dict[key]["similarity_score"] < similarity
                            ):
                                companies_dict[key] = company_data

                    self.log(
                        f"Similarity search found {len(companies_dict)} unique company(ies)"
                    )
                else:
                    self.log(
                        "No similarity matches found",
                        "WARNING",
                    )

            except Exception as e:
                self.log(
                    f"Similarity search failed: {e}",
                    "ERROR",
                )

            # Convert to list and sort by similarity score
            companies = sorted(
                companies_dict.values(),
                key=lambda x: x["similarity_score"],
                reverse=True,
            )

            result["companies"] = companies
            result["total_found"] = len(companies)

            self.log(f"Total unique companies found: {len(companies)}")

        except Exception as e:
            self.log(f"DED query failed: {e}", "ERROR")
            result["error"] = str(e)

        return result

    def _parse_aggregated_license_data(
        self,
        metadata: Dict,
        similarity_score: float,
        match_type: str,
    ) -> Optional[Dict]:
        """
        Parse aggregated license data from ChromaDB metadata
        (from aggregate_ded_extract.py output)

        Args:
            metadata: Metadata dict from ChromaDB
            similarity_score: Similarity score (0-1)
            match_type: "exact" or "similarity"

        Returns:
            Parsed company data dict or None
        """
        try:
            # Extract all fields from aggregated data
            trade_name_en = metadata.get("trade_name_en", "Unknown")
            trade_name_ar = metadata.get("trade_name_ar", "")

            # Parse list fields (stored as JSON strings in metadata)
            license_numbers = self._parse_list_field(
                metadata.get("license_numbers", "[]")
            )
            license_categories = self._parse_list_field(
                metadata.get("license_categories", "[]")
            )
            activities = self._parse_list_field(metadata.get("activities", "[]"))
            partners = self._parse_list_field(metadata.get("partners", "[]"))
            commerce_register_numbers = self._parse_list_field(
                metadata.get(
                    "commerce_register_numbers",
                    "[]",
                )
            )
            issue_authorities = self._parse_list_field(
                metadata.get("issue_authorities", "[]")
            )

            # Get counts
            license_count = int(metadata.get("license_count", 0))
            activity_count = int(metadata.get("activity_count", 0))
            partner_count = int(metadata.get("partner_count", 0))

            # Get dates
            earliest_issue_date = metadata.get("earliest_issue_date", "")
            latest_expiry_date = metadata.get("latest_expiry_date", "")

            return {
                "trade_name_en": trade_name_en,
                "trade_name_ar": trade_name_ar,
                "similarity_score": round(similarity_score, 3),
                "match_type": match_type,
                "license_count": license_count,
                "license_numbers": license_numbers,
                "license_categories": license_categories,
                "activities": activities[:10],  # Limit to top 10 for summary
                "activity_count": activity_count,
                "partners": partners[:10],  # Limit to top 10 for summary
                "partner_count": partner_count,
                "commerce_register_numbers": commerce_register_numbers,
                "issue_authorities": issue_authorities,
                "earliest_issue_date": earliest_issue_date,
                "latest_expiry_date": latest_expiry_date,
            }

        except Exception as e:
            self.log(
                f"Failed to parse aggregated license data: {e}",
                "WARNING",
            )
            return None

    def _parse_list_field(self, field_value: str) -> List:
        """Parse string representation of list"""
        try:
            if isinstance(field_value, list):
                return field_value
            if isinstance(field_value, str):
                # Try to parse as Python literal
                return ast.literal_eval(field_value)
        except:
            pass
        return []

    def _select_best_match_with_llm(
        self,
        top_candidates: List[Dict],
        serp_profile: Optional[Dict],
        company_name: str,
    ) -> Optional[Dict]:
        """
        Use LLM to compare top 3 DED candidates with SERP profile data
        and select the best matching company

        Args:
            top_candidates: Top 3 DED license matches
            serp_profile: SERP profile data from ChromaDB
            company_name: Original company name query

        Returns:
            Selected best match or None
        """
        if not top_candidates:
            return None

        # If no SERP data, return top match by similarity
        if not serp_profile:
            self.log(
                "No SERP data available for comparison, using top similarity match"
            )
            return top_candidates[0]

        self.log("Analyzing top 3 candidates with AI comparison...")

        # Prepare comparison prompt
        comparison_prompt = load_prompt("ded_match_comparison.txt")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", comparison_prompt),
                (
                    "user",
                    "Company Query: {company_name}\n\nSERP Profile Data:\n{serp_data}\n\nTop 3 DED Candidates:\n{ded_candidates}\n\nSelect the best matching DED profile.",
                ),
            ]
        )

        self.log("Comparing business activities, locations, and details...")

        # Invoke LLM for comparison
        self.log("Sending comparison request to AI...")
        chain = prompt | self.llm_connector.llm
        try:
            response = chain.invoke(
                {
                    "company_name": company_name,
                    "serp_data": json.dumps(serp_profile, indent=2),
                    "ded_candidates": json.dumps(
                        [
                            {
                                "rank": i + 1,
                                "trade_name_en": c["trade_name_en"],
                                "trade_name_ar": c["trade_name_ar"],
                                "similarity_score": c["similarity_score"],
                                "license_count": c["license_count"],
                                "license_categories": c["license_categories"],
                                "activities": c["activities"][:5],
                                "partners": c["partners"][:3],
                                "earliest_issue_date": c["earliest_issue_date"],
                            }
                            for i, c in enumerate(top_candidates[:3])
                        ],
                        indent=2,
                    ),
                }
            )
            self.log("AI comparison response received")
        except Exception as llm_error:
            self.log(
                f"LLM comparison failed: {llm_error}",
                "ERROR",
            )
            # Return first candidate as fallback
            return top_candidates[0] if top_candidates else None

        # Parse LLM decision
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            decision = json.loads(content.strip())
            selected_rank = decision.get("selected_rank", 1)
            reasoning = decision.get(
                "reasoning",
                "No reasoning provided",
            )
            confidence = decision.get("confidence", "medium")

            self.log(f"LLM selected rank {selected_rank} with {confidence} confidence")
            self.log(f"```text\nAI REASONING:\n{reasoning}\n```")

            # Get selected candidate (rank is 1-indexed)
            if 1 <= selected_rank <= len(top_candidates):
                selected = top_candidates[selected_rank - 1]
                selected["llm_selection_reasoning"] = reasoning
                selected["llm_confidence"] = confidence
                return selected
            else:
                self.log(
                    f"Invalid rank {selected_rank}, using top match",
                    "WARNING",
                )
                return top_candidates[0]

        except Exception as e:
            self.log(
                f"LLM comparison failed: {e}, using top similarity match",
                "WARNING",
            )
            return top_candidates[0]

    def _generate_summary(self, companies: List[Dict]) -> Dict:
        """
        Generate comprehensive summary of DED license data

        Args:
            companies: List of company data dicts

        Returns:
            Dict with structured summary including active licenses,
            sectors, shareholders, and subsidiaries
        """
        if not companies:
            return {
                "overview": "No UAE DED licenses found",
                "active_licenses": [],
                "potential_sectors": [],
                "shareholder_details": [],
                "subsidiary_info": [],
                "match_confidence": "none",
            }

        # Get top match for detailed summary
        top_match = companies[0]

        # Overview
        total_licenses = sum(c.get("license_count", 0) for c in companies)
        overview = (
            f"Found {len(companies)} matching UAE company(ies) with "
            f"{total_licenses} active license(s). "
            f"Top match: {top_match['trade_name_en']} "
            f"(similarity: {top_match['similarity_score']:.0%}, "
            f"match type: {top_match['match_type']})"
        )

        # Active licenses summary
        active_licenses = []
        for company in companies[:3]:  # Top 3 companies
            license_summary = {
                "company_name": company["trade_name_en"],
                "license_count": company["license_count"],
                "license_numbers": company["license_numbers"][:5],  # Top 5
                "categories": company["license_categories"],
                "earliest_issue": company["earliest_issue_date"],
                "latest_expiry": company["latest_expiry_date"],
                "authorities": company["issue_authorities"],
            }
            active_licenses.append(license_summary)

        # Potential sectors (derived from activities and license categories)
        sectors = set()
        for company in companies:
            sectors.update(company["license_categories"])
            # Extract sector keywords from activities
            for activity in company["activities"][:5]:
                if "trading" in activity.lower():
                    sectors.add("Trading & Commerce")
                elif (
                    "construction" in activity.lower()
                    or "engineering" in activity.lower()
                ):
                    sectors.add("Construction & Engineering")
                elif (
                    "real estate" in activity.lower() or "property" in activity.lower()
                ):
                    sectors.add("Real Estate")
                elif "restaurant" in activity.lower() or "food" in activity.lower():
                    sectors.add("Food & Beverage")
                elif "technology" in activity.lower() or "software" in activity.lower():
                    sectors.add("Technology")
                elif (
                    "consultancy" in activity.lower()
                    or "consulting" in activity.lower()
                ):
                    sectors.add("Professional Services")

        # Shareholder details (from partners)
        shareholder_details = []
        for company in companies[:2]:  # Top 2 companies
            if company["partner_count"] > 0:
                shareholder_details.append(
                    {
                        "company_name": company["trade_name_en"],
                        "total_partners": company["partner_count"],
                        "partners": company["partners"][:10],  # Top 10
                        "note": f"Showing {min(10, company['partner_count'])} of {company['partner_count']} partners",
                    }
                )

        # Subsidiary info (companies with same partners or related trade names)
        subsidiary_info = []
        if len(companies) > 1:
            # Check for potential subsidiaries based on trade name patterns
            base_name = top_match["trade_name_en"].split()[0].upper()
            for company in companies[1:]:
                if base_name in company["trade_name_en"].upper():
                    subsidiary_info.append(
                        {
                            "name": company["trade_name_en"],
                            "relationship": "Potential subsidiary (name similarity)",
                            "licenses": company["license_count"],
                            "activities": company["activities"][:3],
                        }
                    )

        # Match confidence based on similarity score
        top_similarity = top_match["similarity_score"]
        if top_similarity >= 0.95:
            confidence = "very_high"
        elif top_similarity >= 0.80:
            confidence = "high"
        elif top_similarity >= 0.60:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "overview": overview,
            "active_licenses": active_licenses,
            "potential_sectors": sorted(list(sectors)),
            "shareholder_details": shareholder_details,
            "subsidiary_info": subsidiary_info,
            "match_confidence": confidence,
            "total_companies_found": len(companies),
            "total_licenses": total_licenses,
        }

    def execute(self, state: AgentState) -> Dict:
        """
        Execute DED license lookup with hybrid search
        (exact match + similarity search)

        Args:
            state: Shared agent state

        Returns:
            Result with comprehensive DED data
        """
        basic_profile = state.get("enrichments", {})
        canonical_name = basic_profile.get(
            "canonical_name", state.get("company_name", self.company_name)
        )

        self.log(f"Querying DED database for: {canonical_name}")
        self.log("Using hybrid approach: exact match + similarity search")

        # Progress indicator: Start
        self.log("PROGRESS:0:Starting DED lookup")

        try:
            # Query DED database with hybrid approach
            self.log("Searching DED license database...")
            self.log("PROGRESS:20:Querying DED ChromaDB")
            ded_data = self._query_ded_database(canonical_name)

            if ded_data.get("error"):
                self.log(
                    f"DED lookup failed: {ded_data['error']}",
                    "WARNING",
                )
                return {
                    "data": None,
                    "document_type": "uae_ded_license",
                    "metadata": {"error": ded_data["error"]},
                }

            all_companies = ded_data["companies"]
            self.log(f"Found {len(all_companies)} matching company(ies) from DED")
            self.log("PROGRESS:40:Retrieved DED matches")
            self.log("Processing and ranking matches...")

            # Get top 3 candidates for comparison
            top_3_candidates = all_companies[:3]

            if len(top_3_candidates) > 1:
                self.log(
                    f"Comparing top {len(top_3_candidates)} DED matches with SERP data..."
                )
                self.log("PROGRESS:50:Loading SERP profile data")

                # Retrieve SERP profile from ChromaDB
                serp_profile = self._get_serp_profile_from_chromadb(canonical_name)

                self.log(
                    f"SERP profile {'found' if serp_profile else 'not found'} for comparison"
                )

                # Use LLM to select best match
                self.log("PROGRESS:60:AI comparing candidates")
                best_match = self._select_best_match_with_llm(
                    top_3_candidates,
                    serp_profile,
                    canonical_name,
                )
                self.log("PROGRESS:80:Comparison complete")

                if best_match:
                    self.log(f"Selected best match: {best_match['trade_name_en']}")
                    # Put best match first
                    companies = [best_match] + [
                        c
                        for c in all_companies
                        if c["trade_name_en"] != best_match["trade_name_en"]
                    ]
                else:
                    companies = all_companies
            else:
                companies = all_companies
                self.log("PROGRESS:60:Single match found")

            # Generate comprehensive summary
            self.log("PROGRESS:85:Generating summary")
            summary = self._generate_summary(companies)

            self.log(
                f"Generated summary with {len(summary['active_licenses'])} license summaries"
            )
            self.log(
                f"Identified {len(summary['potential_sectors'])} potential sectors"
            )
            self.log(
                f"Found {len(summary['shareholder_details'])} companies with shareholder data"
            )

            self.log("PROGRESS:95:Finalizing results")

            enrichment = {
                "canonical_name": canonical_name,
                "query_type": "hybrid_search",
                "companies": companies,
                "total_companies": len(companies),
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
            }

            self.log("PROGRESS:100:DED lookup complete")

            return {
                "data": enrichment,
                "document_type": "uae_ded_license",
                "metadata": {
                    "source": "uae_ded_chromadb",
                    "search_method": "hybrid",
                    "company_count": len(companies),
                    "match_confidence": summary["match_confidence"],
                },
            }

        except Exception as e:
            self.log(
                f"DED execution error: {e}",
                "ERROR",
            )
            raise
