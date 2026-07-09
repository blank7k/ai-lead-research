"""
Abstract base class for all Research Agent tools.
Lives in its own module to avoid circular imports between registry.py
and any concrete tool (e.g. contact_discovery.py) that must implement it.
"""

from abc import ABC, abstractmethod
from typing import Tuple
from models.domain import Lead


class IResearchTool(ABC):
    """Abstract interface defining the execution contract for all Research Agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Standardised unique identifier of the tool."""
        ...

    @abstractmethod
    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        """
        Execute the research tool on the current Lead context.

        Returns:
            Tuple[Lead, str]: The updated Lead model and a user-facing trace string.
        """
        ...
