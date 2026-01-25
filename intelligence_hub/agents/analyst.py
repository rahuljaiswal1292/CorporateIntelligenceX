import logging
import json
from intelligence_hub.graph.state import AgentState
from intelligence_hub.connectors.llm import LLMConnector
from intelligence_hub.connectors.pinecone_client import PineconeConnector

logger = logging.getLogger(__name__)

class AnalystAgent:
    """
    Agent 4: The Analyst.
    Generates strategic banking insights using LLM + RAG.
    """
    def __init__(self):
        self.llm = LLMConnector()
        self.pc = PineconeConnector()

    def run(self, state: AgentState) -> AgentState:
        logger.info("Analyst: Processing data...")
        logs = state.get("logs", [])
        
        ticker = state.get("ticker", "Unknown")
        company_name = state.get("company_name", "Unknown")
        
        # 1. Summarize Profile (if raw data exists)
        # We assume 'scraped_data' might be passed in state by the Scraper Agent (Graph)
        # For now, let's assume 'financial_data' holds the scraped result in the current graph flow
        scraped_data = state.get("financial_data", {})
        
        description = state.get("meta", {}).get("description", "")
        
        # If we have raw wiki data, summarize it
        sources = scraped_data.get("sources", [])
        wiki_source = next((s for s in sources if s["title"] == "Wikipedia"), None)
        
        if wiki_source and "raw_html_snippet" in str(scraped_data): 
             # Only if we suspect we have raw data to summarize
             # (In a real implementation, we'd pass the specific raw string. 
             # For now, we'll verify if we need to summarize)
             pass 

        # 2. RAG Search (Context)
        logs.append("Analyst: Querying Vector DB for context...")
        context_chunks = self.pc.search(f"{ticker} risks opportunities", top_k=3)
        context_str = "\n".join(context_chunks)
        
        # 3. Construct Prompt for Insights
        prompt = f"""
        You are a Corporate Banking Relationship Manager.
        Analyze the data for {company_name} ({ticker}) to generate 5 strategic banking opportunities.
        
        Financial Data: {json.dumps(scraped_data.get('financials', {}), indent=2)}
        Market Context: {context_str}
        
        Return STRICTLY JSON format with these exact keys for each item: 
        category, finding, source, trigger, action.
        """
        
        logs.append("Analyst: Sending prompt to Gemini 1.5 Pro...")
        
        # 4. Call LLM
        response_text = self.llm.analyze(prompt)
        
        try:
            # Clean markdown code blocks if present
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            insights = json.loads(clean_text)
            logs.append(f"Analyst: Generated {len(insights)} strategic insights.")
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            insights = []
            logs.append("Analyst: Error in insight generation.")

        return {
            "insights": insights,
            "logs": logs,
            # Pass through other state
            "ticker": ticker,
            "company_name": company_name
        }

    def summarize_profile(self, text: str) -> str:
        """Summarizes raw text into a company profile."""
        prompt = f"Summarize this company profile in 3 paragraphs (Business, Segments, Key Strengths):\n\n{text[:5000]}"
        return self.llm.analyze(prompt)
