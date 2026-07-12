from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Sequence


class LLMProvider(ABC):
    """Provider-agnostic LLM surface. Swap implementations without touching call sites."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        model: str,
        system: Optional[str] = None,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.3,
    ) -> str:
        """Return text completion. If schema is set, return JSON matching that schema."""

    @abstractmethod
    def embed(self, texts: Sequence[str], *, model: str) -> list[list[float]]:
        """Return embedding vectors for each input text."""
