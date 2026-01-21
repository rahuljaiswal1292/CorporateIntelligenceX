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
        logger.info("Analyst: Generating insights...")
        logs = state.get("logs", [])
        logs.append("Analyst: Querying Vector DB for context...")
        
        # 1. RAG Search
        context_chunks = self.pc.search(f"{state['ticker']} risks opportunities", top_k=3)
        context_str = "\n".join(context_chunks)
        
        # 2. Construct Prompt
        fin_data = state.get("financial_data", {})
        prompt = f"""
        You are a Corporate Banking Relationship Manager.
        Analyze the following data for {state['company_name']} ({state['ticker']}) and generate 5 strategic opportunities.
        
        Financials: {fin_data}
        Context: {context_str}
        
        Return STRICTLY JSON format with keys: category, finding, source, trigger, action.
        """
        
        logs.append("Analyst: Sending prompt to Gemini 1.5 Pro...")
        
        # 3. Call LLM
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
            "logs": logs
        }
