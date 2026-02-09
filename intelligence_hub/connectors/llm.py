import os
import logging
import json
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMConnector:
    """
    Connector for OpenAI GPT-4 & Embeddings.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if self.api_key:
            self.llm = ChatOpenAI(
                model="gpt-4-turbo",
                openai_api_key=self.api_key,
                temperature=0.3
            )
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=self.api_key
            )
            self.mode = "LIVE"
        else:
            self.llm = None
            self.embeddings = None
            self.mode = "MOCK"
            logger.warning("OPENAI_API_KEY not found. Running in MOCK MODE.")

    def embed(self, text: str) -> List[float]:
        """Generates a vector embedding for the given text."""
        if self.mode == "LIVE":
            try:
                return self.embeddings.embed_query(text)
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
                return [0.0] * 1536 # Fallback (OpenAI dim)
        else:
            return [0.1] * 1536 # Mock vector

    def analyze(self, prompt: str) -> str:
        """
        Sends a prompt to the LLM and returns the text response.
        """
        logger.info(f"[{self.mode}] Running Analysis...")
        
        if self.mode == "LIVE":
            try:
                response = self.llm.invoke(prompt)
                return response.content
            except Exception as e:
                logger.error(f"LLM Error: {str(e)}")
                return self._get_mock_insights() # Fallback on error
        else:
            return self._get_mock_insights()

    def _get_mock_insights(self) -> str:
        """Returns a mocked JSON string of strategic insights."""
        mock_data = [
            {
                "category": "Lending Opportunity",
                "finding": "AED 2.5B Refinancing Gap identified in 2025 maturities.",
                "source": "Annual Report 2023 - Note 14 (Sukuk)",
                "trigger": "Significant debt maturity approaching in Q3 2025.",
                "action": "Propose early refinancing of Sukuk with a Green Loan structure."
            },
            {
                "category": "Trade Finance",
                "finding": "AED 12B Export Revenue growing at 15% YoY.",
                "source": "Financial Statements - Segment Reporting",
                "trigger": "Rising cross-border receivables days (DSO > 90).",
                "action": "Pitch Supply Chain Finance (SCF) to optimize working capital."
            },
            {
                "category": "Operational Efficiency",
                "finding": "Digital Transformation budget increased by 20%.",
                "source": "CEO Message 2023",
                "trigger": "Focus on AI and automation integration.",
                "action": "Cross-sell API Banking solution for automated reconciliation."
            },
            {
                "category": "KYC / Compliance",
                "finding": "New subsidiary established in Saudi Arabia.",
                "source": "Investor Presentation Q3 2024",
                "trigger": "Cross-border entity requires fresh KYC due diligence.",
                "action": "Initiate KYC refresh and request trade license for new KSA entity."
            },
            {
                "category": "Strategic Growth",
                "finding": "Expansion into Real Estate Development sector.",
                "source": "Press Release Jan 2024",
                "trigger": "New revenue stream requires specialized project finance.",
                "action": "Engage Real Estate specialized coverage team for Project Finance origination."
            }
        ]
        return json.dumps(mock_data, indent=2)
