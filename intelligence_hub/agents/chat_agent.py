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

    def answer_query(
        self,
        query: str,
        ticker: str,
        history: List[Dict] = None,
        extra_context: str = None,
    ) -> str:
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
            You are a Strategic Executive Assistant and Corporate Intelligence Expert advising C-suite executives.
            Your goal is to provide precise, data-backed insights about {self.company_name} ({ticker}).
            
            PRIORITY SOURCE: The "Current Dashboard Discovery" block contains real-time findings from our latest investigation. If information is present there, it is the ABSOLUTE TRUTH.
            
            STRUCTURE & FORMATTING (CRITICAL):
            1. START WITH A PARAGRAPH: Begin with 2-3 sentences of strategic context or a direct high-level answer. 
            2. USE MARKDOWN LISTS: For all metrics, risks, or details, use BULLET POINTS (-). 
            3. DOUBLE NEWLINES: Place a BLANK LINE (double newline) between the introductory paragraph and the first bullet point, and between each bullet point.
            4. FORBID INLINE LISTS: Never write "1. Point one 2. Point two" inside a paragraph. Every point MUST be on its own line starting with a dash (-).
            5. BOLD HIGHLIGHTS: Use **BOLD TEXT** for every single currency value (e.g., **AED 2.5B**), date, or key business entity.
            6. SCANNABILITY: Every response MUST be easily scannable with clear vertical separation between points.
            
            Answering Guidelines:
            - POSITIVE DATA-FIRST: Start by highlighting what we DO know. Lead with the most impressive or relevant figure found.
            - AUTHORITATIVE TONE: Use phrases like "Our intelligence indicates..." or "Strategic assessment of {self.company_name} shows...".
            - CAVEATS AT THE END: If data is missing, provide related values first, then add a small 1-sentence note at the very end.
            - NO HALLUCINATION: Only use numbers present in the context.
            
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
