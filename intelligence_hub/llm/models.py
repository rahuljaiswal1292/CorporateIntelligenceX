"""
LLM Model Configuration

Defines available LLM models and their configurations.
"""

from enum import Enum
from typing import Dict, Any


class LLMModel(str, Enum):
    """Available LLM models"""
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_35_TURBO = "gpt-3.5-turbo"


class LLMConfig:
    """LLM Configuration class for managing model parameters"""
    
    def __init__(
        self,
        model: str = LLMModel.GPT_4_TURBO,
        temperature: float = 0.3,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0
    ):
        """
        Initialize LLM configuration
        
        Args:
            model: The LLM model to use (from LLMModel enum)
            temperature: Controls randomness (0.0-1.0)
            top_p: Nucleus sampling parameter (0.0-1.0)
            frequency_penalty: Penalize frequent tokens (0.0-2.0)
        """
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
    
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
            frequency_penalty=config_dict.get("frequency_penalty", 0.0)
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
            "frequency_penalty": self.frequency_penalty
        }
    
    @staticmethod
    def get_available_models() -> list:
        """
        Get list of available model names
        
        Returns:
            List of model names
        """
        return [model.value for model in LLMModel]
