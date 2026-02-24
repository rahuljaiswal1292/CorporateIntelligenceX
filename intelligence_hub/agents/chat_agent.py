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

    def answer_query(self, query: str, ticker: str, history: List[Dict] = None) -> str:
        """
        RAG-enabled answering logic.
        """
        self.log(f"Processing query for {ticker}: {query}")

        # 1. Retrieve relevant context from VectorDB
        context_results = self.vector_manager.query(ticker, query, n_results=5)

        context_text = "\n\n".join(
            [
                f"[Source: {r['metadata']['source']}]\n{r['text']}"
                for r in context_results
            ]
        )

        if not context_text:
            context_text = "No direct information found in internalized documents."

        # 2. Build Prompt
        system_prompt = textwrap.dedent(
            f"""
            You are a Strategic Executive Assistant and Corporate Intelligence Expert.
            Your goal is to provide precise, data-backed insights about {self.company_name} ({ticker}).
            
            Guidelines:
            - Use the provided CONTEXT to answer the question.
            - If the context doesn't contain the answer, say you don't have that specific data but mention what you DO know if relevant.
            - Keep the tone professional, executive, and objective.
            - If there are tables or financial figures in the context, synthesize them clearly.
            - Always cite the source files mentioned in brackets like [Source: filename].
            
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
