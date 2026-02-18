import json
from typing import Dict, Optional, Callable
import pandas as pd
import os
from intelligence_hub.graph.state import AgentState
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
from intelligence_hub.config.config import DATA_DIRECTORY
from .base_agent import BaseAgent


class AnalystAgent(BaseAgent):
    """
    Agent 4: The Analyst.
    Generates strategic banking insights using LLM + RAG.
    """

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="Analyst Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Decide if analyst should run

        Args:
            state: Shared agent state

        Returns:
            (should_run, reasoning)
        """
        # Analyst always runs to generate insights
        return (True, "Analyst generates strategic insights from all available data")

    def execute(self, state: AgentState) -> Dict:
        """
        Execute analyst workflow

        Args:
            state: Shared agent state

        Returns:
            Result with strategic insights
        """
        ticker = state.get("ticker", "Unknown")
        company_name = state.get("company_name", "Unknown")

        self.log(f"Generating strategic insights for: {company_name}")

        # Get scraped financial data
        scraped_data = state.get("financial_data", {})

        # 2. RAG Search (Context) using CorporateProfileStore
        context_str = ""
        if self.profile_store:
            # Search for relevant context in ChromaDB
            search_results = self.profile_store.search_by_description(
                query=f"{ticker} {company_name} risks opportunities",
                threshold=0.3,
                max_results=3,
            )

            context_chunks = []
            for result in search_results:
                # Extract relevant text from search results
                if "document" in result:
                    context_chunks.append(result["document"])
                elif "description" in result.get("metadata", {}):
                    context_chunks.append(result["metadata"]["description"])

            context_str = "\n".join(context_chunks)
            self.log(f"Retrieved {len(context_chunks)} context chunks from ChromaDB")
        else:
            self.log(
                "No profile_store available, proceeding without RAG context", "WARNING"
            )

        # 3. Construct Prompt for Insights
        prompt = f"""
        You are a Corporate Banking Relationship Manager.
        Analyze the data for {company_name} ({ticker}) to generate 5 strategic banking opportunities.
        
        Financial Data: {json.dumps(scraped_data.get('financials', {}), indent=2)}
        Market Context: {context_str}
        
        Return STRICTLY JSON format with these exact keys for each item: 
        category, finding, source, trigger, action.
        """

        self.log("Generating strategic insights with LLM...")

        # 4. Call LLM
        response_text = self.llm_connector.analyze(prompt)

        try:
            # Clean markdown code blocks if present
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            insights = json.loads(clean_text)
            self.log(f"Generated {len(insights)} strategic insights", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to parse LLM response: {e}", "ERROR")
            insights = []

        return {
            "data": insights,
            "document_type": "strategic_insights",
            "metadata": {
                "company_name": company_name,
                "ticker": ticker,
                "insight_count": len(insights),
            },
        }

    def _get_daily_summary(self, exchange: str, company: str) -> Dict:
        r"""
        Reads validation summary from D:\University\CorporateIntelligenceX\data\<exchange>\<company>\daily_summary\structured\*.xls
        """
        try:
            # Construct path
            search_pattern = os.path.join(
                DATA_DIRECTORY,
                exchange,
                company,
                "daily_summary",
                "structured",
            )
            files = [
                f for f in os.listdir(search_pattern) if f.lower().endswith(".xls")
            ]

            if not files:
                self.log(f"No daily summary found at {search_pattern}", "WARNING")
                return {}

            # Read the first file found
            file_path = search_pattern + "/" + files[0]
            self.log(f"Reading daily summary from {file_path}")

            try:
                # Attempt to read as standard Excel (using explicit engine if needed, but auto detection is usually safer unless specific)
                # If engine="xlrd" is forced for .xls but content is HTML, it fails.
                df = pd.read_excel(file_path, engine="xlrd")
            except Exception as excel_err:
                # Fallback: Check if it's an HTML file masked as XLS
                self.log(
                    f"Standard Excel read failed ({excel_err}), attempting HTML parse...",
                    "WARNING",
                )
                try:
                    dfs = pd.read_html(file_path)
                    if dfs:
                        df = dfs[0]
                    else:
                        raise ValueError("No tables found in HTML-masked file")
                except Exception as html_err:
                    self.log(f"Failed to read as HTML too: {html_err}", "ERROR")
                    return {}

            # Convert to dict
            data = df.to_dict(orient="records")
            return {"data": data, "source_file": os.path.basename(file_path)}

        except Exception as e:
            self.log(f"Failed to read daily summary: {e}", "ERROR")
            return {}

    def run(self, state):
        """
        Run analyst workflow

        Args:
            state: Current agent state

        Returns:
            Updated agent state
        """
        logs = []

        # Check if should execute
        should_run, reasoning = self.should_execute(state)

        if not should_run:
            self.log(f"Skipping analyst: {reasoning}")
            logs.append(f"Analyst: Skipped - {reasoning}")
            return {**state, "logs": logs, "insights": []}

        # Execute analysis
        try:
            logs.append("Analyst: Processing data...")
            result = self.execute(state)
            insights = result.get("data", [])

            logs.append(f"Analyst: Generated {len(insights)} strategic insights.")

            # Generate Final Report
            final_report = self.generate_final_report(state, insights)
            logs.append("Analyst: Generated Final Report.")

            # Update financial_data with daily summary
            financial_data = state.get("financial_data", {})
            exchange = state.get("exchange", "Unknown")

            # Assuming 'company_name' in state matches directory structure.
            # If strictly 'ticker' is used for folders, we might need to change this.
            # But prompt said "data\<exchange>\<company>", likely company name.
            # Let's try both company_name and ticker if one fails?
            # Sticking to company_name as per instruction.
            daily_summary = self._get_daily_summary(
                exchange, state.get("ticker", "Unknown")
            )

            if daily_summary:
                financial_data["daily_summary"] = daily_summary

            return {
                **state,  # Merge original state to preserve all keys
                "insights": insights,
                "final_report": final_report,
                "logs": logs,
                "financial_data": financial_data,  # Updated with daily summary
            }

        except Exception as e:
            self.log(f"Analyst execution failed: {e}", "ERROR")
            logs.append("Analyst: Error in insight generation.")
            return {
                **state,  # Merge original state on error too
                "insights": [],
                "logs": logs,
            }

    def generate_final_report(self, state: AgentState, insights: list) -> Dict:
        """Generates a comprehensive final report."""
        company_name = state.get("company_name", "Unknown")
        ticker = state.get("ticker", "Unknown")
        enrichments = state.get("enrichments", {})

        # Create a summary of enrichments
        profile_summary = {
            "canonical_name": enrichments.get("canonical_name"),
            "description": enrichments.get("description"),
            "industry": enrichments.get("industry"),
            "headquarters": enrichments.get("headquarters"),
            "website": enrichments.get("website"),
        }

        prompt = f"""
        Generate a professional Executive Banking Intelligence Report for {company_name} ({ticker}).
        
        Company Profile:
        {json.dumps(profile_summary, indent=2)}
        
        Strategic Insights & Opportunities:
        {json.dumps(insights, indent=2)}
        
         Return STRICTLY JSON format being concise and professional with the below keys.
        1. Executive_summary
        2. Company_overview
        3. Strategic_banking_opportunities
        4. Key_risks_and_considerations
        """

        try:
            response_text = self.llm_connector.analyze(prompt)
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            self.log(f"Failed to generate final report: {e}", "ERROR")
            return {"error": "Final report generation failed", "details": str(e)}

    def summarize_profile(self, text: str) -> str:
        """Summarizes raw text into a company profile."""
        prompt = f"Summarize this company profile in 3 paragraphs (Business, Segments, Key Strengths):\n\n{text[:5000]}"
        return self.llm_connector.analyze(prompt)
