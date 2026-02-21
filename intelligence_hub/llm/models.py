"""
LLM Model Configuration

Defines available LLM models and their configurations.
"""

from enum import Enum
from typing import Dict, Any, Optional


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    GOOGLE = "google"


class LLMModel(str, Enum):
    """Available LLM models (grouped by provider)"""

    # OpenAI models
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_35_TURBO = "gpt-3.5-turbo"
    # Google Gemini models
    GEMINI_2_FLASH = "models/gemini-2.0-flash-001"
    GEMINI_15_FLASH = "models/gemini-1.5-flash"
    GEMINI_15_PRO = "models/gemini-1.5-pro"

    @staticmethod
    def for_provider(provider: "LLMProvider") -> list:
        """Return the model names available for a given provider."""
        openai_models = [
            LLMModel.GPT_4_TURBO,
            LLMModel.GPT_4O,
            LLMModel.GPT_35_TURBO,
        ]
        google_models = [
            LLMModel.GEMINI_2_FLASH,
            LLMModel.GEMINI_15_FLASH,
            LLMModel.GEMINI_15_PRO,
        ]
        if provider == LLMProvider.GOOGLE:
            return [m.value for m in google_models]
        return [m.value for m in openai_models]

    @staticmethod
    def get_all_models() -> list:
        """Return every available model name across all providers (for flat UI dropdown)."""
        return [m.value for m in LLMModel]

    @staticmethod
    def detect_provider(model: str) -> "LLMProvider":
        """
        Infer the provider from a model name string.
        - Any model starting with 'gemini' or 'models/gemini' → Google
        - Everything else (gpt-*, o1, o3, etc.) → OpenAI
        """
        m = str(model).lower()
        if m.startswith("gemini") or m.startswith("models/gemini"):
            return LLMProvider.GOOGLE
        return LLMProvider.OPENAI


class LLMConfig:
    """LLM Configuration class for managing model parameters"""

    def __init__(
        self,
        model: str = LLMModel.GPT_4_TURBO,
        temperature: float = 0.3,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        provider: str = LLMProvider.OPENAI,
        api_key: Optional[str] = None,
    ):
        """
        Initialize LLM configuration

        Args:
            model: The LLM model to use (from LLMModel enum)
            temperature: Controls randomness (0.0-1.0)
            top_p: Nucleus sampling parameter (0.0-1.0)
            frequency_penalty: Penalize frequent tokens (0.0-2.0)
            provider: LLM provider — 'openai' or 'google'
            api_key: Optional API key override (falls back to env vars)
        """
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.provider = provider
        self.api_key = api_key

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LLMConfig":
        """
        Create LLMConfig from dictionary

        Args:
            config_dict: Dictionary containing model configuration

        Returns:
            LLMConfig instance
        """
        return cls(
            model=config_dict.get("model", LLMModel.GPT_4_TURBO),
            temperature=config_dict.get("temperature", 0.3),
            top_p=config_dict.get("top_p", 1.0),
            frequency_penalty=config_dict.get("frequency_penalty", 0.0),
            provider=config_dict.get("provider", LLMProvider.OPENAI),
            api_key=config_dict.get("api_key"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert LLMConfig to dictionary

        Returns:
            Dictionary representation of configuration
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "provider": self.provider,
            "api_key": self.api_key,
        }

    @staticmethod
    def get_available_models() -> list:
        """
        Get list of all available model names

        Returns:
            List of model names
        """
        return [model.value for model in LLMModel]
