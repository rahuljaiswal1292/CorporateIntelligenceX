"""Prompt templates for LLM-driven research"""

from pathlib import Path


def load_prompt(prompt_name: str) -> str:
    """Load a prompt template from file

    Args:
        prompt_name: Name of the prompt file (including extension)

    Returns:
        Prompt template content
    """
    prompt_file = Path(__file__).parent / f"{prompt_name}"
    with open(prompt_file, "r", encoding="utf-8") as f:
        return f.read()


__all__ = ["load_prompt"]
