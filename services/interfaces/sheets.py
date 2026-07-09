from abc import ABC, abstractmethod
from typing import List
from models.domain import Lead


class ISheetsService(ABC):
    """Clean architecture interface for spreadsheet synchronization operations (e.g., Google Sheets)."""

    @abstractmethod
    def append_leads(self, spreadsheet_id: str, leads: List[Lead]) -> bool:
        """Append one or more researched leads to the spreadsheet."""
        pass

    @abstractmethod
    def update_lead(self, spreadsheet_id: str, lead: Lead) -> bool:
        """Update an existing lead entry in the spreadsheet matching by domain/name."""
        pass

    @abstractmethod
    def read_all_brands(self, spreadsheet_id: str) -> List[dict]:
        """Read a list of brand website URLs/names from a spreadsheet to seed the backlog."""
        pass
