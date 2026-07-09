from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class Contacts(BaseModel):
    """Structured contact arrays on a lead."""
    emails: List[str] = Field(default_factory=list, description="Public email addresses found.")
    phones: List[str] = Field(default_factory=list, description="Public phone numbers found.")
    addresses: List[str] = Field(default_factory=list, description="HQ or retail mailing addresses.")


class Socials(BaseModel):
    """Structured social media handles / profile URLs on a lead."""
    instagram: Optional[str] = Field(None, description="Instagram profile URL.")
    linkedin: Optional[str] = Field(None, description="LinkedIn company page URL.")
    facebook: Optional[str] = Field(None, description="Facebook page URL.")
    twitter: Optional[str] = Field(None, description="Twitter / X profile URL.")


class Lead(BaseModel):
    """Refactored Lead domain model holding consolidated target brand data."""
    brand_name: str = Field(..., description="Name of the brand.")
    founder_name: Optional[str] = Field(None, description="Name of the brand's founder.")
    website: Optional[str] = Field(None, description="Official homepage URL.")
    category: str = Field("Fashion/D2C", description="Market category/vertical.")
    
    contacts: Contacts = Field(default_factory=Contacts, description="Grouped business contacts.")
    socials: Socials = Field(default_factory=Socials, description="Grouped social endpoints.")
    
    confidence_score: float = Field(0.0, description="Completeness score (0.0 to 1.0).")
    sources: List[str] = Field(default_factory=list, description="Sources crawled during research.")
    execution_trace: List[str] = Field(default_factory=list, description="Chronological trace of tools invoked.")
    
    is_verified: bool = Field(False, description="Flag indicating if critical info was validated.")
    synced_to_sheets: bool = Field(False, description="Whether sync'd with Google Sheets.")
    synced_to_db: bool = Field(False, description="Whether sync'd with database.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def missing_fields(self) -> List[str]:
        """Dynamically computes missing data points to guide the Research Agent."""
        missing = []
        if not self.website or self.website == "unknown":
            missing.append("website")
        if not self.contacts.emails:
            missing.append("emails")
        if not self.contacts.phones:
            missing.append("phones")
        if not self.founder_name:
            missing.append("founder")
        return missing
