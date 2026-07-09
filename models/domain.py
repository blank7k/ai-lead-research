from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ContactInfo(BaseModel):
    """Domain model representing the contact information gathered for a brand."""
    emails: List[str] = Field(default_factory=list, description="List of business email addresses found.")
    phones: List[str] = Field(default_factory=list, description="List of contact phone numbers found.")
    instagram_url: Optional[str] = Field(None, description="Instagram profile URL.")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company page URL.")
    twitter_url: Optional[str] = Field(None, description="Twitter / X profile URL.")
    facebook_url: Optional[str] = Field(None, description="Facebook page URL.")
    contact_page_url: Optional[str] = Field(None, description="URL of the brand's contact or about page.")
    physical_address: Optional[str] = Field(None, description="Physical headquarters or store address if found.")
    raw_sources: List[str] = Field(default_factory=list, description="List of source URLs where contact info was scraped.")


class Brand(BaseModel):
    """Domain model representing a D2C brand to be researched."""
    id: Optional[str] = Field(None, description="Unique identifier for the brand (e.g. UUID from DB).")
    name: str = Field(..., description="Name of the D2C fashion brand.")
    website_url: str = Field(..., description="Main website URL of the brand.")
    domain: str = Field(..., description="Extracted domain name of the brand (e.g. brand.com).")
    category: Optional[str] = Field("Fashion/D2C", description="Market category (e.g. apparel, footwear, accessories).")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Lead(BaseModel):
    """Domain model representing a completed Lead, joining a Brand with its ContactInfo."""
    brand: Brand
    contact_info: ContactInfo
    is_verified: bool = Field(False, description="Flag indicating if the contact details have been verified.")
    confidence_score: float = Field(0.0, description="Confidence score of research completeness (0.0 to 1.0).")
    research_notes: Optional[str] = Field(None, description="Internal agent notes or logs about the research process.")
    synced_to_sheets: bool = Field(False, description="Whether this lead has been exported to Google Sheets.")
    synced_to_db: bool = Field(False, description="Whether this lead has been saved to Supabase.")
    last_researched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
