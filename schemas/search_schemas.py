from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class BrandSearchResult(BaseModel):
    """Structured output representing target URLs found for a brand via web search."""
    brand_name: str = Field(..., description="The queried name of the D2C brand.")
    official_website: Optional[str] = Field(None, description="Extracted brand official homepage URL.")
    instagram_url: Optional[str] = Field(None, description="Extracted brand Instagram profile URL.")
    facebook_url: Optional[str] = Field(None, description="Extracted brand Facebook profile URL.")
    linkedin_url: Optional[str] = Field(None, description="Extracted brand LinkedIn company page URL.")
    google_maps_url: Optional[str] = Field(None, description="Extracted Google Maps / Google Business URL if found.")
    raw_results: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="The raw list of search hits retrieved (useful for backup/auditing)."
    )
