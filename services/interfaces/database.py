from abc import ABC, abstractmethod
from typing import List, Optional
from models.domain import Brand, Lead


class IDatabaseService(ABC):
    """Clean architecture interface for persistence operations (e.g., Supabase)."""

    @abstractmethod
    def save_brand(self, brand: Brand) -> Brand:
        """Persist a new D2C brand or update an existing one."""
        pass

    @abstractmethod
    def get_brand(self, brand_id: str) -> Optional[Brand]:
        """Fetch a single brand by its unique identifier."""
        pass

    @abstractmethod
    def get_brands_by_status(self, status: str, limit: int = 10) -> List[Brand]:
        """Get brands matching a specific status (e.g., 'pending', 'processing')."""
        pass

    @abstractmethod
    def save_lead(self, lead: Lead) -> Lead:
        """Persist a researched lead, updating both brand and contact details."""
        pass

    @abstractmethod
    def get_lead_by_brand_id(self, brand_id: str) -> Optional[Lead]:
        """Retrieve the contact lead for a given brand."""
        pass
