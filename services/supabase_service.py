from typing import List, Optional
from loguru import logger
from supabase import Client, create_client
from config.settings import settings
from models.domain import Brand, Lead
from services.interfaces.database import IDatabaseService


class SupabaseService(IDatabaseService):
    """Concrete implementation of IDatabaseService interfacing with Supabase."""

    def __init__(self) -> None:
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.client: Optional[Client] = None
        
        if self.url and self.key:
            logger.info("Initializing Supabase client.")
            self.client = create_client(self.url, self.key)
        else:
            logger.warning("Supabase credentials not fully configured; operating in mock/offline mode.")

    def save_brand(self, brand: Brand) -> Brand:
        logger.info(f"Saving brand '{brand.name}' to Supabase.")
        # DB scaffolding logic
        if self.client:
            # Concrete implementation will go here
            pass
        return brand

    def get_brand(self, brand_id: str) -> Optional[Brand]:
        logger.info(f"Fetching brand by ID '{brand_id}' from Supabase.")
        if self.client:
            # Concrete implementation will go here
            pass
        return None

    def get_brands_by_status(self, status: str, limit: int = 10) -> List[Brand]:
        logger.info(f"Fetching up to {limit} brands with status '{status}' from Supabase.")
        if self.client:
            # Concrete implementation will go here
            pass
        return []

    def save_lead(self, lead: Lead) -> Lead:
        logger.info(f"Saving lead for brand '{lead.brand.name}' to Supabase.")
        if self.client:
            # Concrete implementation will go here
            pass
        return lead

    def get_lead_by_brand_id(self, brand_id: str) -> Optional[Lead]:
        logger.info(f"Fetching lead details for brand ID '{brand_id}' from Supabase.")
        if self.client:
            # Concrete implementation will go here
            pass
        return None
