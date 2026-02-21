"""
Enhanced Corporate Profile Vector Store using ChromaDB

Modular implementation with support for:
- Dual collection architecture (names + details)
- Flexible storage with automatic chunking
- Multiple document types (PDF, HTML, Excel, JSON, text)
- Hybrid search (exact match + semantic)
- Phase 2A enrichment data types
"""

import chromadb
from chromadb.config import Settings
import json
from datetime import datetime
from typing import Dict, List, Optional
import openai
import os

from intelligence_hub.config.config import (
    OPENAI_API_KEY,
    CHROMADB_PERSIST_DIRECTORY,
    CHROMADB_COLLECTION_NAME,
    SIMILARITY_THRESHOLD,
    MAX_SEARCH_RESULTS,
)

# Document types supported in Phase 2A enrichment
DOCUMENT_TYPES = [
    "basic_profile",  # Phase 1: SerpAPI + LLM extraction
    "wikipedia",  # Phase 2A: Wikipedia enrichment
    "news",  # Phase 2A: News articles
    "uae_ded_license",  # Phase 2A: DED licenses
    "comprehensive_profile",  # Phase 3: Final aggregated profile
]

# Import modular utilities
from .content_extractors import (
    create_name_text,
    create_details_text,
    create_profile_text,
)
from .metadata_handler import (
    calculate_completeness,
    get_missing_fields,
    is_profile_complete,
)
from .search_utils import (
    format_search_results,
    is_exact_match,
    is_similar_match,
    create_exact_match_result,
    filter_suggestions_by_prefix,
)


class CorporateProfileStore:
    """Corporate Profile Storage with flexible schema"""

    def __init__(
        self,
        persist_directory: str = None,
        logger_callback=None,
    ):
        """Initialize ChromaDB for storing company profiles

        Args:
            persist_directory: Path to ChromaDB storage directory
            logger_callback: Optional callback function for logging messages
        """
        self.logger_callback = logger_callback
        if persist_directory is None:
            persist_directory = CHROMADB_PERSIST_DIRECTORY

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Create two collections with COSINE similarity metric
        # 1. Name store - for fast, accurate company name matching
        self.name_collection = self.client.get_or_create_collection(
            name=f"{CHROMADB_COLLECTION_NAME}_names",
            metadata={
                "description": "Company names and identifiers for search",
                "hnsw:space": "cosine",
            },
        )

        # 2. Details store - for full company profiles and documents
        self.details_collection = self.client.get_or_create_collection(
            name=f"{CHROMADB_COLLECTION_NAME}_details",
            metadata={
                "description": "Full company profiles and documents",
                "hnsw:space": "cosine",
            },
        )

        # Legacy collection reference (points to name store for backward compatibility)
        self.collection = self.name_collection

        # Initialize OpenAI client
        openai.api_key = OPENAI_API_KEY

    def _log(self, message: str):
        """Internal logging method"""
        if self.logger_callback:
            self.logger_callback(message)

    # ==================== SEARCH METHODS ====================

    def search_companies(self, query: str, threshold: float = None) -> List[Dict]:
        """Search for companies by matching against canonical_name and tried_names

        Args:
            query: Company name from UI
            threshold: Minimum similarity score for semantic search (0-1)

        Returns:
            List of matching companies with similarity scores
        """
        if threshold is None:
            threshold = SIMILARITY_THRESHOLD

        if not query.strip():
            return []

        try:
            query_lower = query.lower().strip()
            original_query = query.strip()

            # Get all records
            all_records = self.name_collection.get(include=["metadatas"])
            all_ids = self.name_collection.get()["ids"]

            matches = []

            # Step 1: Check exact matches against canonical_name and tried_names
            for i, meta in enumerate(all_records["metadatas"]):
                canonical_name = meta.get("canonical_name", "").lower()
                raw_names_str = meta.get("raw_names", "").lower()
                record_id = all_ids[i]

                is_exact = is_exact_match(
                    query_lower,
                    canonical_name,
                    raw_names_str,
                )

                if is_exact:
                    matches.append(
                        {
                            "meta": meta,
                            "record_id": record_id,
                            "is_exact": True,
                        }
                    )

            # Step 2: If no exact match, try similar matching
            if not matches:
                for i, meta in enumerate(all_records["metadatas"]):
                    canonical_name = meta.get("canonical_name", "").lower()
                    raw_names_str = meta.get("raw_names", "").lower()
                    record_id = all_ids[i]

                    is_similar = is_similar_match(
                        query_lower,
                        canonical_name,
                        raw_names_str,
                    )

                    if is_similar:
                        matches.append(
                            {
                                "meta": meta,
                                "record_id": record_id,
                                "is_exact": False,
                            }
                        )

            # Process matches
            if matches:
                # Take the first (most recent) match
                match = matches[0]
                meta = match["meta"]
                record_id = match["record_id"]
                is_exact = match["is_exact"]

                # NOTE: We do NOT automatically add non-exact search terms to raw_names
                # This prevents pollution where unrelated search terms get permanently
                # associated with wrong companies. Only exact matches should be considered
                # for automatic addition, or names should be manually curated.

                self._log(
                    f"Found match for '{query}': {meta.get('canonical_name', '')} (exact={is_exact})"
                )

                # Return the match
                result = create_exact_match_result(meta)
                return [result]

            # Step 3: No match found - fall back to semantic search
            self._log(f"🔍 No direct match, trying semantic search: {query}")
            results = self.name_collection.query(
                query_texts=[query],
                n_results=MAX_SEARCH_RESULTS,
                include=[
                    "metadatas",
                    "documents",
                    "distances",
                ],
            )

            return format_search_results(results, threshold)

        except Exception as e:
            self._log(f"⚠️ Error in search_companies: {e}")
            return []

    def search_by_description(
        self,
        query: str,
        threshold: float = 0.3,
        max_results: int = 5,
    ) -> List[Dict]:
        """Search companies by semantic similarity in details collection

        Args:
            query: Description or semantic query
            threshold: Minimum similarity score
            max_results: Maximum number of results

        Returns:
            List of matching companies
        """
        try:
            results = self.details_collection.query(
                query_texts=[query],
                n_results=max_results,
                include=[
                    "metadatas",
                    "documents",
                    "distances",
                ],
            )

            return format_search_results(results, threshold)

        except Exception as e:
            self._log(f"⚠️ Error in search_by_description: {e}")
            return []

    def get_all_companies(self) -> List[str]:
        """Get list of all company names in the store

        Returns:
            List of company names
        """
        try:
            all_records = self.name_collection.get(include=["metadatas"])
            companies = list(
                set(
                    meta.get("company_name")
                    for meta in all_records["metadatas"]
                    if meta.get("company_name")
                )
            )
            return sorted(companies)
        except Exception as e:
            self._log(f"⚠️ Error getting all companies: {e}")
            return []

    def get_company_suggestions(
        self,
        query: str,
        max_suggestions: int = 10,
    ) -> List[Dict]:
        """Get autocomplete suggestions for company search

        Args:
            query: Partial company name or ticker
            max_suggestions: Maximum suggestions to return

        Returns:
            List of suggestion dictionaries
        """
        if not query.strip():
            return []

        try:
            query_lower = query.lower().strip()
            all_records = self.name_collection.get(include=["metadatas"])

            return filter_suggestions_by_prefix(
                all_records["metadatas"],
                query_lower,
                max_suggestions,
            )

        except Exception as e:
            self._log(f"⚠️ Error getting suggestions: {e}")
            return []

    def find_similar_company(
        self,
        query: str,
        max_results: int = 3,
    ) -> List[Dict]:
        """Find similar companies using semantic search

        Args:
            query: Company name to search for
            max_results: Maximum number of results to return

        Returns:
            List of dictionaries with canonical_name, distance, and metadata
        """
        if not query.strip():
            return []

        try:
            # Use semantic search on name collection
            results = self.name_collection.query(
                query_texts=[query],
                n_results=max_results,
                include=[
                    "metadatas",
                    "distances",
                ],
            )

            if not results or not results["ids"] or len(results["ids"][0]) == 0:
                return []

            # Format results
            matches = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0

                matches.append(
                    {
                        "canonical_name": metadata.get(
                            "canonical_name",
                            "Unknown",
                        ),
                        "distance": distance,
                        "metadata": metadata,
                    }
                )

            return matches

        except Exception as e:
            self._log(f"⚠️ Error finding similar companies: {e}")
            return []

    # ==================== STORAGE METHODS ====================

    def store_company_profile(
        self,
        company_name: str,
        profile_data: Dict,
        search_query: str = None,
        document_type: str = "profile",
    ) -> str:
        """Store a company profile with flexible storage

        Args:
            company_name: Name of the company
            profile_data: Dictionary containing all profile fields
            search_query: Original search query (optional)
            document_type: Type of document (profile, pdf, excel, html, text, json)

        Returns:
            profile_id: Unique identifier for this profile
        """
        # Generate unique ID
        timestamp = int(datetime.now().timestamp())
        profile_id = f"{company_name.lower().replace(' ', '_')}_{timestamp}"

        # Check for existing profiles with same canonical name and remove them
        canonical_name = profile_data.get("canonical_name", company_name)

        # Collect existing raw_names before deletion
        existing_raw_names = []
        try:
            all_records = self.name_collection.get(include=["metadatas"])
            ids_to_delete = []

            for i, meta in enumerate(all_records["metadatas"]):
                if meta.get("canonical_name", "").lower() == canonical_name.lower():
                    ids_to_delete.append(all_records["ids"][i])
                    # Preserve existing raw names
                    raw_names_str = meta.get("raw_names", "")
                    if raw_names_str:
                        existing_raw_names.extend(
                            [n.strip() for n in raw_names_str.split(",") if n.strip()]
                        )

            if ids_to_delete:
                self._log(
                    f"Removing {len(ids_to_delete)} old profile(s) for '{canonical_name}'"
                )
                self.name_collection.delete(ids=ids_to_delete)

                # Also delete from details collection
                for old_id in ids_to_delete:
                    base_id = old_id.replace("_name", "")
                    try:
                        self.details_collection.delete(where={"profile_id": base_id})
                    except Exception:
                        pass
        except Exception as e:
            self._log(f"Warning: Could not check for duplicates: {e}")

        # 1. Store in NAME collection (for search)
        name_text = create_name_text(profile_data, company_name)

        # Build list of raw names (search queries that led to this profile)
        # Include: existing raw names, current company name, canonical name, and tried_names from search
        raw_names_list = existing_raw_names + [
            company_name,
            canonical_name,
        ]

        # Extract tried_names from _metadata if available
        metadata = profile_data.get("_metadata", {})
        tried_names = metadata.get("tried_names", [])
        if tried_names and isinstance(tried_names, list):
            raw_names_list.extend(tried_names)

        # Remove duplicates (case-insensitive) and empty strings
        seen = set()
        unique_raw_names = []
        for name in raw_names_list:
            name_str = str(name).strip()
            name_lower = name_str.lower()
            if name_str and name_lower not in seen:
                seen.add(name_lower)
                unique_raw_names.append(name_str)

        raw_names_str = ", ".join(unique_raw_names)

        name_metadata = {
            "company_name": company_name,
            "canonical_name": profile_data.get("canonical_name", company_name),
            "raw_names": raw_names_str,  # Store all search aliases
            "ticker": profile_data.get("ticker", ""),
            "industry": profile_data.get("industry", ""),
            "timestamp": datetime.now().isoformat(),
            # Social media profiles
            "twitter": profile_data.get("twitter", ""),
            "linkedin": profile_data.get("linkedin", ""),
            "instagram": profile_data.get("instagram", ""),
            "youtube": profile_data.get("youtube", ""),
            "facebook": profile_data.get("facebook", ""),
            # Additional info
            "website": profile_data.get("website", ""),
            "ceo": profile_data.get("ceo", ""),
            "headquarters": profile_data.get("headquarters", ""),
        }

        self.name_collection.add(
            documents=[name_text],
            metadatas=[name_metadata],
            ids=[f"{profile_id}_name"],
        )

        # 2. Store in DETAILS collection (flexible storage)
        # Serialize profile_data for storage
        profile_json = json.dumps(profile_data, ensure_ascii=False)

        # Create text content for embedding
        details_text = create_details_text(profile_data)

        # Create metadata
        details_metadata = {
            "company_name": company_name,
            "canonical_name": profile_data.get("canonical_name", company_name),
            "document_type": document_type,
            "profile_data": profile_json,
            "timestamp": datetime.now().isoformat(),
        }

        # Add key fields to metadata
        for key in [
            "industry",
            "website",
        ]:
            if key in profile_data:
                details_metadata[key] = str(profile_data[key])

        self.details_collection.add(
            documents=[details_text],
            metadatas=[details_metadata],
            ids=[f"{profile_id}_details"],
        )

        return profile_id

    def update_company_profile(self, company_name: str, new_data: Dict) -> bool:
        """Update existing company profile or create new one

        Args:
            company_name: Name of company to update
            new_data: New data to merge/update

        Returns:
            True if successful
        """
        try:
            # Check if company exists
            existing = self.get_company_profile(company_name)

            if existing:
                # Update existing profile
                existing_data = (
                    json.loads(existing["document"])
                    if isinstance(existing["document"], str)
                    else existing["metadata"]
                )
                merged_data = {
                    **existing_data,
                    **new_data,
                }

                # Delete old profile
                self.collection.delete(where={"company_name": {"$eq": company_name}})

                # Store updated profile
                self.store_company_profile(company_name, merged_data)
                return True
            else:
                # Create new profile
                self.store_company_profile(company_name, new_data)
                return True

        except Exception as e:
            self._log(f"⚠️ Error updating profile: {e}")
            return False

    # ==================== RETRIEVAL METHODS ====================

    def get_company_profile(self, company_name: str) -> Optional[Dict]:
        """Get the most recent profile for a specific company from name collection

        Args:
            company_name: Company name to retrieve

        Returns:
            Company profile or None
        """
        results = self.collection.query(
            query_texts=[company_name],
            n_results=MAX_SEARCH_RESULTS,
            where={"company_name": {"$eq": company_name}},
            include=["metadatas", "documents"],
        )

        if results["metadatas"] and results["metadatas"][0]:
            return {
                "company_name": company_name,
                "metadata": results["metadatas"][0][0],
                "document": results["documents"][0][0],
            }
        return None

    def get_full_profile_from_details(self, company_name: str) -> Optional[Dict]:
        """Get the full profile with all fields from details collection

        Args:
            company_name: Name of the company to retrieve

        Returns:
            Dictionary with all profile fields, or None if not found
        """
        try:
            # Query details collection
            results = self.details_collection.get(
                where={
                    "$or": [
                        {"company_name": company_name},
                        {"canonical_name": company_name},
                    ]
                },
                include=[
                    "metadatas",
                    "documents",
                ],
            )

            if not results["ids"]:
                return None

            # Get the most recent profile
            metadata = results["metadatas"][0]

            # Try to get profile_data from metadata
            if "profile_data" in metadata:
                profile_json = metadata["profile_data"]
                return json.loads(profile_json)

            # Otherwise return the metadata as profile
            return metadata

        except Exception as e:
            self._log(f"⚠️ Error getting full profile: {e}")
            return None

    def get_enrichment_data(
        self,
        canonical_name: str,
        document_type: str = None,
    ) -> Dict[str, List[Dict]]:
        """Retrieve enrichment data for a company

        Args:
            canonical_name: Canonical name of the company
            document_type: Optional filter for specific document type

        Returns:
            Dictionary mapping document_type to list of results
        """
        where_clause = {"canonical_name": canonical_name}
        if document_type:
            where_clause["document_type"] = document_type

        results = self.details_collection.get(
            where=where_clause,
            include=["metadatas", "documents"],
        )

        enrichment_data = {}
        if results["metadatas"]:
            for i, meta in enumerate(results["metadatas"]):
                doc_type = meta.get("document_type", "unknown")
                if doc_type not in enrichment_data:
                    enrichment_data[doc_type] = []

                # Parse detailed JSON if available
                data = meta
                if "profile_data" in meta:
                    try:
                        data = json.loads(meta["profile_data"])
                    except:
                        pass

                enrichment_data[doc_type].append(data)

        return enrichment_data

    def store_enrichment_data(
        self,
        canonical_name: str,
        enrichment_data: Dict,
        document_type: str,
    ) -> bool:
        """Store specific enrichment data (e.g., wikipedia, news)

        Args:
            canonical_name: Standardized company name
            enrichment_data: Data to store
            document_type: Type of enrichment

        Returns:
            True if successful
        """
        try:
            # Generate ID
            timestamp = int(datetime.now().timestamp())
            data_id = f"{canonical_name.lower().replace(' ', '_')}_{document_type}_{timestamp}"

            # Create text representation
            text_content = f"{document_type.upper()} Data for {canonical_name}: {str(enrichment_data)[:1000]}"

            # Serialize data
            data_json = json.dumps(enrichment_data, ensure_ascii=False)

            # Metadata
            metadata = {
                "canonical_name": canonical_name,
                "document_type": document_type,
                "profile_data": data_json,
                "timestamp": datetime.now().isoformat(),
            }

            self.details_collection.add(
                documents=[text_content],
                metadatas=[metadata],
                ids=[data_id],
            )
            return True

        except Exception as e:
            self._log(f"Error storing enrichment data: {e}")
            return False

    def store_financials(self, ticker: str, data: Dict) -> bool:
        """Store financial data with timestamp for cache management"""
        try:
            timestamp = datetime.now().isoformat()
            # We use 'financials' as document type
            # Data typically contains 'financials' (dict) and 'sources' (list)

            # Create a textual representation for search if needed
            text_content = f"Financial Data for {ticker}: {str(data)[:500]}..."

            # Serialize
            data_json = json.dumps(data, ensure_ascii=False)

            metadata = {
                "ticker": ticker,
                "document_type": "financials",
                "timestamp": timestamp,
                "data": data_json,
            }

            # Upsert (overwrite existing for this ticker)
            doc_id = f"{ticker}_financials"

            self.details_collection.upsert(
                ids=[doc_id], documents=[text_content], metadatas=[metadata]
            )
            return True
        except Exception as e:
            self._log(f"Error storing financials: {e}")
            return False

    def get_financials(self, ticker: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Retrieve financial data if fresh"""
        try:
            doc_id = f"{ticker}_financials"
            results = self.details_collection.get(ids=[doc_id], include=["metadatas"])

            if not results["ids"]:
                return None

            metadata = results["metadatas"][0]
            timestamp_str = metadata.get("timestamp")

            if not timestamp_str:
                return None

            # Check staleness
            stored_time = datetime.fromisoformat(timestamp_str)
            if (datetime.now() - stored_time).total_seconds() > (max_age_hours * 3600):
                self._log(f"Financial data for {ticker} is stale.")
                return None

            # Deserialize
            if "data" in metadata:
                return json.loads(metadata["data"])
            return None

        except Exception as e:
            self._log(f"Error retrieving financials: {e}")
            return None

    def store_vectors(self, vectors: List[tuple]) -> bool:
        """
        Store vectors (chunks) directly.
        Args:
            vectors: List of (id, embedding_values, metadata)
        """
        try:
            ids = [v[0] for v in vectors]
            embeddings = [v[1] for v in vectors]
            metadatas = [v[2] for v in vectors]
            documents = [m.get("text", "") for m in metadatas]

            self.details_collection.upsert(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
            )
            return True
        except Exception as e:
            self._log(f"Error storing vectors: {e}")
            return False
