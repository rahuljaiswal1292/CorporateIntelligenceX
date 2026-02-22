import os
import logging
import json
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from typing import List, Dict, Any, Optional, Union
from intelligence_hub.llm.models import LLMConfig, LLMModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models known to support Vision (image_url)
# Models known to support Vision (image_url) - Be conservative here
VISION_MODELS = {"gpt-4o", "gpt-4o-mini"}


class LLMConnector:
    """
    Connector for OpenAI GPT-4 & Embeddings.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[Union[LLMConfig, Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
    ):
        """
        Initialize LLM Connector

        Args:
            api_key: OpenAI API key (optional, defaults to env var)
            config: LLMConfig object or dict with configuration (optional)
            model: Model name (optional, overrides config)
            temperature: Temperature parameter (optional, overrides config)
            top_p: Top-p parameter (optional, overrides config)
            frequency_penalty: Frequency penalty (optional, overrides config)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        # Handle config parameter
        if config is not None:
            if isinstance(config, dict):
                llm_config = LLMConfig.from_dict(config)
            else:
                llm_config = config
        else:
            llm_config = LLMConfig()

        # Individual parameters override config
        self.model = model if model is not None else llm_config.model
        self.temperature = (
            temperature if temperature is not None else llm_config.temperature
        )
        self.top_p = top_p if top_p is not None else llm_config.top_p
        self.frequency_penalty = (
            frequency_penalty
            if frequency_penalty is not None
            else llm_config.frequency_penalty
        )

        if self.api_key:
            self.llm = ChatOpenAI(
                model=self.model,
                openai_api_key=self.api_key,
                temperature=self.temperature,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
            )
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small", openai_api_key=self.api_key
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
                return [0.0] * 1536  # Fallback (OpenAI dim)
        else:
            return [0.1] * 1536  # Mock vector

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
                return self._get_mock_insights()  # Fallback on error
        else:
            return self._get_mock_insights()

    def analyze_with_images(self, prompt: str, images: List[str]) -> str:
        """
        Sends a prompt and a list of base64 encoded images to the LLM.
        """
        logger.info(
            f"[{self.mode}] Running Vision Analysis with {len(images)} images..."
        )

        if self.mode == "LIVE":
            content_parts = [{"type": "text", "text": prompt}]
            for img_b64 in images:
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    }
                )

            message = HumanMessage(content=content_parts)

            # Try primary model first if it's in vision list
            if self.model in VISION_MODELS:
                try:
                    response = self.llm.invoke([message])
                    return response.content
                except Exception as e:
                    # Catch the specific vision error and fall back
                    error_msg = str(e)
                    if "image_url is only supported by certain models" in error_msg:
                        logger.warning(
                            f"Model {self.model} claimed vision support but failed. Falling back to gpt-4o."
                        )
                    else:
                        logger.error(f"LLM Vision Primary Error: {error_msg}")
                        raise e  # Re-raise if it's not a model compatibility issue

            # Fallback path (used if primary not in list OR if primary failed with model error)
            try:
                logger.info("Using gpt-4o fallback for vision analysis.")
                vision_llm = ChatOpenAI(
                    model="gpt-4o",
                    openai_api_key=self.api_key,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
                response = vision_llm.invoke([message])
                return response.content
            except Exception as e:
                logger.error(f"LLM Vision Fallback Error: {str(e)}")
                return self._get_mock_insights()
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
                "action": "Propose early refinancing of Sukuk with a Green Loan structure.",
            },
            {
                "category": "Trade Finance",
                "finding": "AED 12B Export Revenue growing at 15% YoY.",
                "source": "Financial Statements - Segment Reporting",
                "trigger": "Rising cross-border receivables days (DSO > 90).",
                "action": "Pitch Supply Chain Finance (SCF) to optimize working capital.",
            },
            {
                "category": "Operational Efficiency",
                "finding": "Digital Transformation budget increased by 20%.",
                "source": "CEO Message 2023",
                "trigger": "Focus on AI and automation integration.",
                "action": "Cross-sell API Banking solution for automated reconciliation.",
            },
            {
                "category": "KYC / Compliance",
                "finding": "New subsidiary established in Saudi Arabia.",
                "source": "Investor Presentation Q3 2024",
                "trigger": "Cross-border entity requires fresh KYC due diligence.",
                "action": "Initiate KYC refresh and request trade license for new KSA entity.",
            },
            {
                "category": "Strategic Growth",
                "finding": "Expansion into Real Estate Development sector.",
                "source": "Press Release Jan 2024",
                "trigger": "New revenue stream requires specialized project finance.",
                "action": "Engage Real Estate specialized coverage team for Project Finance origination.",
            },
        ]
        return json.dumps(mock_data, indent=2)
