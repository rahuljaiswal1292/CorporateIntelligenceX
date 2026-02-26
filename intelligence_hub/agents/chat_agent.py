import os
import json
from typing import Dict, List, Optional, Any, Callable
from intelligence_hub.agents.base_agent import BaseAgent
from intelligence_hub.graph.state import AgentState
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.vector_manager import VectorManager
import textwrap


class ChatAgent(BaseAgent):
    """
    Assistant agent that uses RAG (via VectorManager) to answer user queries
    based on processed corporate intelligence.
    """

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        vector_manager: Optional[VectorManager] = None,
    ):
        super().__init__(
            agent_name="Executive Assistant",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
        )
        self.vector_manager = vector_manager or VectorManager()

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """Always ready to chat."""
        return True, "User requested a query."

    def execute(self, state: AgentState) -> Dict:
        """Handled by the main chat loop usually, but available for pipeline integration."""
        return {"status": "ready"}

    def answer_query(self, query: str, ticker: str, history: List[Dict] = None, extra_context: str = None) -> str:
        """
        RAG-enabled answering logic with optional dashboard context.
        """
        self.log(f"Processing query for {ticker}: {query}")

        # 1. Retrieve relevant context from VectorDB
        context_results = self.vector_manager.query(ticker, query, n_results=5)

        context_blocks = []
        if extra_context:
            context_blocks.append(f"[Current Dashboard Discovery]\n{extra_context}")

        for r in context_results:
            context_blocks.append(f"[Source: {r['metadata']['source']}]\n{r['text']}")

        context_text = "\n\n".join(context_blocks)

        if not context_text:
            context_text = "No direct information found in internalized documents."

        # 2. Build Prompt
        system_prompt = textwrap.dedent(
            f"""
            You are a Strategic Executive Assistant and Corporate Intelligence Expert.
            Your goal is to provide precise, data-backed insights about {self.company_name} ({ticker}).
            
            PRIORITY SOURCE: The "Current Dashboard Discovery" block contains real-time findings from our latest investigation. If information is present there, it is the ABSOLUTE TRUTH and should be used before any other records.
            
            Guidelines:
            - ALWAYS ground your answer in the provided CONTEXT. 
            - Use a concrete and authoritative tone. Start your answers or key points with phrases like "As per the primary dashboard data, I found..." or "According to the latest filings, {self.company_name} is...".
            - Be specific with numbers, dates, and names.
            - NO GENERIC FALLBACKS: Avoid phrases like "specific figures are not detailed" if there is ANY related figure in the context. If you see a percentage like "28%" for international operations, report it exactly.
            - If details are missing, synthesize what IS available and offer the closest relevant information while clearly stating what specific detail is not present.
            - Professionalism is key: You are advising a C-suite executive.
            
            CONTEXT:
            {context_text}
        """
        ).strip()

        # 3. Call LLM
        messages = [{"role": "system", "content": system_prompt}]

        if history:
            messages.extend(history[-5:])  # Last 5 messages for context

        messages.append({"role": "user", "content": query})

        response = self.llm_connector.call_llm(messages)
        return response
