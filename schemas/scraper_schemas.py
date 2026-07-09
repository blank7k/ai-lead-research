from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class WebsiteResearchResult(BaseModel):
    """Structured output representing contact details crawled from a brand's domain."""
    emails: List[str] = Field(default_factory=list, description="Public business emails found.")
    phones: List[str] = Field(default_factory=list, description="Public phone numbers found.")
    whatsapp_numbers: List[str] = Field(default_factory=list, description="Direct WhatsApp numbers/links found.")
    postal_addresses: List[str] = Field(default_factory=list, description="Physical postal/HQ addresses extracted.")
    social_links: Dict[str, str] = Field(
        default_factory=dict, 
        description="Social media profile URLs mapped by platform name (e.g., {'instagram': '...'})."
    )
    contact_page_url: Optional[str] = Field(None, description="Identified contact page URL.")
    visited_urls: List[str] = Field(
        default_factory=list, 
        description="All internal domain pages visited during the crawl."
    )
