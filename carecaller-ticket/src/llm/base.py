from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict | None = None


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    def __init__(self, model: str | None = None):
        self.model = model

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        ...

    @abstractmethod
    def complete_json(self, prompt: str, system: str = "") -> dict:
        """Return parsed JSON from the LLM."""
        ...
