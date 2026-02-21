import os
import logging
import json
from typing import List, Dict, Any, Optional, Union
from langchain_core.messages import HumanMessage

from intelligence_hub.llm.models import LLMConfig, LLMModel, LLMProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMConnector:
    """
    Connector for LLM providers: OpenAI GPT-4 or Google Gemini.

    Provider and API key are resolved automatically:
      1. Explicit constructor args
      2. Values in the config dict / LLMConfig object
      3. LLM_PROVIDER env var
      4. Auto-detected from the model name (gemini-* → Google, gpt-* → OpenAI)
      5. Provider-specific env vars: GOOGLE_API_KEY / OPENAI_API_KEY
      6. Generic fallback: LLM_API_KEY
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[Union[LLMConfig, Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        provider: Optional[str] = None,
    ):
        # --- Resolve config object ---
        if config is not None:
            llm_config = (
                LLMConfig.from_dict(config) if isinstance(config, dict) else config
            )
        else:
            llm_config = LLMConfig()

        # Individual parameter overrides
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

        # --- Resolve provider ---
        # Priority: 1. Explicit arg, 2. Auto-detect from model name (if model provided), 3. LLM_PROVIDER env var
        resolved_provider = provider
        if not resolved_provider and model:
            resolved_provider = LLMModel.detect_provider(model)
        if not resolved_provider:
            resolved_provider = os.getenv("LLM_PROVIDER")

        self.provider = str(resolved_provider or "openai").lower()

        # --- Resolve API key ---
        # Priority: explicit arg > config api_key > provider-specific env var > LLM_API_KEY
        if api_key:
            resolved_key = api_key
        elif getattr(llm_config, "api_key", None):
            resolved_key = llm_config.api_key
        elif self.provider == LLMProvider.GOOGLE:
            resolved_key = os.getenv("GOOGLE_API_KEY") or os.getenv("LLM_API_KEY")
        else:
            resolved_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

        self.api_key = resolved_key

        # --- Initialise LLM & Embeddings ---
        if self.api_key:
            self._init_llm()
        else:
            self.llm = None
            self.embeddings = None
            self.mode = "MOCK"
            logger.warning(
                f"No API key found for provider '{self.provider}'. Running in MOCK MODE. "
                f"Set GOOGLE_API_KEY or OPENAI_API_KEY (or LLM_API_KEY) in your .env file."
            )

    def _init_llm(self):
        """Initialise the correct LangChain LLM and embeddings for the resolved provider."""
        try:
            if self.provider == LLMProvider.GOOGLE:
                from langchain_google_genai import (
                    ChatGoogleGenerativeAI,
                    GoogleGenerativeAIEmbeddings,
                )

                self.llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=self.api_key,
                    temperature=self.temperature,
                )

                embed_model = os.getenv("EMBEDDING_MODEL", "embedding-001")
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model=embed_model,
                    google_api_key=self.api_key,
                )
                self.mode = "LIVE (Google Gemini)"
                display_model = self.model.replace("models/", "")
                logger.info(f"LLM initialised: Google Gemini — {display_model}")

            else:
                # Default: OpenAI
                from langchain_openai import ChatOpenAI, OpenAIEmbeddings

                self.llm = ChatOpenAI(
                    model=self.model,
                    openai_api_key=self.api_key,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    frequency_penalty=self.frequency_penalty,
                )
                self.embeddings = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    openai_api_key=self.api_key,
                )
                self.mode = "LIVE (OpenAI)"
                logger.info(f"LLM initialised: OpenAI — {self.model}")

        except ImportError as e:
            logger.error(
                f"Missing dependency for provider '{self.provider}': {e}. "
                "Install: pip install langchain-google-genai  (for Google)"
            )
            self.llm = None
            self.embeddings = None
            self.mode = "MOCK"

        except Exception as e:
            logger.error(
                f"Failed to initialise LLM for provider '{self.provider}': {e}"
            )
            self.llm = None
            self.embeddings = None
            self.mode = "MOCK"

    def embed(self, text: str) -> List[float]:
        """Generates a vector embedding for the given text."""
        if self.embeddings:
            try:
                return self.embeddings.embed_query(text)
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
                return [0.0] * 1536
        return [0.1] * 1536  # Mock vector

    def analyze(self, prompt: str) -> str:
        """Sends a prompt to the LLM and returns the text response."""
        logger.info(f"[{self.mode}] Running Analysis...")
        if self.llm is not None:
            try:
                response = self.llm.invoke(prompt)
                return response.content
            except Exception as e:
                logger.error(f"LLM Error: {str(e)}")
                return self._get_mock_insights()
        return self._get_mock_insights()

    def analyze_with_images(self, prompt: str, images: List[str]) -> str:
        """Sends a prompt and a list of base64 encoded images to the LLM."""
        logger.info(
            f"[{self.mode}] Running Vision Analysis with {len(images)} images..."
        )
        if self.llm is not None:
            try:
                content_parts = [{"type": "text", "text": prompt}]
                for img_b64 in images:
                    content_parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                        }
                    )
                message = HumanMessage(content=content_parts)
                response = self.llm.invoke([message])
                return response.content
            except Exception as e:
                logger.error(f"LLM Vision Error: {str(e)}")
                return self._get_mock_insights()
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
