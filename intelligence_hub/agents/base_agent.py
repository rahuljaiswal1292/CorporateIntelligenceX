"""
Base Agent Class for Multi-Agent Workflow

Provides common functionality for all worker agents including:
- Logging with progress callback
- Data storage in company-specific directories
- ChromaDB integration
- Decision making framework
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from abc import ABC, abstractmethod

from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.storage.corporate_profile_store import (
    CorporateProfileStore,
)
from intelligence_hub.config.config import DATA_DIRECTORY


class BaseAgent(ABC):
    """Base class for all research agents"""

    def __init__(
        self,
        agent_name: str,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        """
        Initialize base agent

        Args:
            agent_name: Name of the agent (e.g., "Wikipedia Agent")
            company_name: Company being researched
            llm_connector: Shared LLM connector instance
            log_callback: Function to call for progress updates
            profile_store: ChromaDB store instance
        """
        self.agent_name = agent_name
        self.company_name = company_name
        self.llm_connector = llm_connector
        self.log_callback = log_callback
        self.profile_store = profile_store
        # Create company data directory
        self.data_dir = Path(DATA_DIRECTORY) / self._sanitize_company_name(company_name)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Agent state
        self.status = "initialized"
        self.result = None
        self.error = None

    def _sanitize_company_name(self, name: str) -> str:
        """Convert company name to safe directory name"""
        return name.lower().replace(" ", "_").replace(".", "").replace(",", "")

    def log(self, message: str, level: str = "INFO"):
        """
        Log message with simple formatting (no emojis, no markdown)

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{self.agent_name}] {level}: {message}"

        if self.log_callback:
            self.log_callback(formatted_message + "\n")
        else:
            print(formatted_message)

    def save_to_disk(self, data: Dict, filename: str) -> str:
        """
        Save data to company-specific directory with timestamp subdirectory

        Args:
            data: Data to save
            filename: Filename (without timestamp prefix)

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create timestamped subdirectory
        timestamped_dir = self.data_dir / timestamp
        timestamped_dir.mkdir(parents=True, exist_ok=True)

        filepath = timestamped_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                if isinstance(data, str):
                    f.write(data)
                else:
                    json.dump(
                        data,
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

            self.log(
                f"Saved data to {filepath}",
                "SUCCESS",
            )
            return str(filepath)
        except Exception as e:
            self.log(
                f"Failed to save data: {e}",
                "ERROR",
            )
            return ""

    def check_existing_profile(
        self,
        document_type: str = None,
        max_age_days: int = 30,
    ) -> Optional[Dict]:
        """
        Check if a recent profile exists in ChromaDB

        Args:
            document_type: Type of document to check (None for any)
            max_age_days: Maximum age in days to consider profile as recent

        Returns:
            Existing profile data or None
        """
        if not self.profile_store:
            return None

        try:
            from datetime import timedelta

            # Get enrichment data for this company
            enrichment_data = self.profile_store.get_enrichment_data(
                canonical_name=self.company_name,
                document_type=document_type,
            )

            if not enrichment_data:
                return None

            # Check if any data is recent enough
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            for (
                doc_type,
                data_list,
            ) in enrichment_data.items():
                for data in data_list:
                    if isinstance(data, dict):
                        timestamp_str = data.get("timestamp")
                        if timestamp_str:
                            try:
                                data_timestamp = datetime.fromisoformat(
                                    timestamp_str.replace(
                                        "Z",
                                        "+00:00",
                                    )
                                )
                                if data_timestamp > cutoff_date:
                                    self.log(
                                        f"Found recent {doc_type} data from {timestamp_str}",
                                        "INFO",
                                    )
                                    return data
                            except:
                                pass

            return None

        except Exception as e:
            self.log(
                f"Error checking existing profile: {e}",
                "WARNING",
            )
            return None

    def save_to_chromadb(self, data: Dict, document_type: str) -> bool:
        """
        Save enrichment data to ChromaDB

        Args:
            data: Enrichment data
            document_type: Type of document (wikipedia, news, etc.)

        Returns:
            Success status
        """
        if not self.profile_store:
            self.log(
                "No ChromaDB store available",
                "WARNING",
            )
            return False

        try:
            canonical_name = data.get(
                "canonical_name",
                self.company_name,
            )
            success = self.profile_store.store_enrichment_data(
                canonical_name=canonical_name,
                enrichment_data=data,
                document_type=document_type,
            )

            if success:
                self.log(
                    f"Stored {document_type} data in ChromaDB",
                    "SUCCESS",
                )
            else:
                self.log(
                    f"Failed to store {document_type} data in ChromaDB",
                    "ERROR",
                )

            return success
        except Exception as e:
            self.log(
                f"ChromaDB storage error: {e}",
                "ERROR",
            )
            return False

    @abstractmethod
    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Decide if this agent should execute based on state

        Args:
            state: Shared agent state

        Returns:
            (should_run, reasoning) tuple
        """
        pass

    @abstractmethod
    def execute(self, state: AgentState) -> Dict:
        """
        Execute the agent's research task

        Args:
            state: Shared agent state

        Returns:
            Result dictionary with enrichment data
        """
        pass

    def run(self, state: AgentState) -> Dict:
        """
        Main execution method with decision making

        Args:
            state: Shared agent state

        Returns:
            Result with status, data, and metadata
        """
        self.log(f"Starting {self.agent_name}")
        self.status = "deciding"

        # Step 1: Decide if should execute
        should_run, reasoning = self.should_execute(state)
        self.log(f"Decision: {'EXECUTE' if should_run else 'SKIP'}")
        self.log(f"```text\nReasoning: {reasoning}\n```")

        if not should_run:
            self.status = "skipped"
            return {
                "agent": self.agent_name,
                "status": "skipped",
                "reasoning": reasoning,
                "data": None,
            }

        # Step 2: Execute research
        self.status = "executing"
        try:
            result = self.execute(state)
            self.status = "completed"
            self.result = result

            # Step 3: Save to disk
            if result and result.get("data"):
                self.save_to_disk(
                    result["data"],
                    f"{self.agent_name.lower().replace(' ', '_')}.json",
                )

            # Step 4: Save to ChromaDB if applicable
            if result and result.get("data") and result.get("document_type"):
                self.save_to_chromadb(
                    result["data"],
                    result["document_type"],
                )

            self.log(
                f"Completed successfully",
                "SUCCESS",
            )
            return {
                "agent": self.agent_name,
                "status": "completed",
                "reasoning": reasoning,
                "data": result.get("data"),
                "metadata": result.get("metadata", {}),
            }

        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            self.log(f"Execution failed: {e}", "ERROR")
            return {
                "agent": self.agent_name,
                "status": "failed",
                "reasoning": reasoning,
                "error": str(e),
                "data": None,
            }
