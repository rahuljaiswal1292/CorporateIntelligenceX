import json
from typing import Dict, Optional, Callable
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.storage.corporate_profile_store import CorporateProfileStore
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

    def run(self, state: AgentState) -> AgentState:
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

            return {
                "insights": insights,
                "final_report": final_report,
                "logs": logs,
                # Pass through other state
                "ticker": state.get("ticker", "Unknown"),
                "company_name": state.get("company_name", "Unknown"),
            }

        except Exception as e:
            self.log(f"Analyst execution failed: {e}", "ERROR")
            logs.append("Analyst: Error in insight generation.")
            return {
                "insights": [],
                "logs": logs,
                "ticker": state.get("ticker", "Unknown"),
                "company_name": state.get("company_name", "Unknown"),
            }

    def generate_final_report(self, state: AgentState, insights: list) -> str:
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
        
        Format the report in Markdown being concise and professional.
        Include sections:
        1. Executive Summary
        2. Company Overview
        3. Strategic Banking Opportunities
        4. Key Risks & Considerations
        """

        try:
            return self.llm_connector.analyze(prompt)
        except Exception as e:
            self.log(f"Failed to generate final report: {e}", "ERROR")
            return "Final report generation failed."

    def summarize_profile(self, text: str) -> str:
        """Summarizes raw text into a company profile."""
        prompt = f"Summarize this company profile in 3 paragraphs (Business, Segments, Key Strengths):\n\n{text[:5000]}"
        return self.llm_connector.analyze(prompt)
