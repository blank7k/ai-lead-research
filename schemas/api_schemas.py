from typing import List, Optional
from pydantic import BaseModel, Field
from models.domain import Lead


class BrandInput(BaseModel):
    """Schema for supplying a brand to the research system."""
    name: str = Field(..., description="Name of the brand to research.")
    website_url: str = Field(..., description="Website home URL of the brand.")
    category: Optional[str] = Field(None, description="Optional custom category or vertical.")


class LeadResearchRequest(BaseModel):
    """Request payload to initiate research on one or more D2C brands."""
    brands: List[BrandInput] = Field(..., min_items=1, description="List of brands to process.")
    export_to_sheets: bool = Field(True, description="Whether to export completed leads to Google Sheets.")
    save_to_supabase: bool = Field(True, description="Whether to persist leads in Supabase database.")


class LeadResearchResponse(BaseModel):
    """Response payload returned after completing research requests."""
    request_id: str = Field(..., description="Unique UUID tracking this research run.")
    status: str = Field(..., description="Final status of the request (e.g. COMPLETED, PARTIAL_SUCCESS, FAILED).")
    processed_count: int = Field(0, description="Number of brands successfully processed.")
    leads: List[Lead] = Field(default_factory=list, description="List of researched Lead results.")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during the run.")
