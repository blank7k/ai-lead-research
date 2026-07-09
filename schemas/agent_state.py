from typing import Annotated, Dict, List, Optional
from pydantic import BaseModel, Field
from models.domain import Brand, ContactInfo


def merge_logs(left: List[str], right: List[str]) -> List[str]:
    """Helper reducer to append agent execution logs in LangGraph state."""
    return left + right


def merge_scraped_pages(left: List[Dict], right: List[Dict]) -> List[Dict]:
    """Helper reducer to combine unique scraped page metadata."""
    seen_urls = {item["url"] for item in left}
    combined = list(left)
    for item in right:
        if item["url"] not in seen_urls:
            combined.append(item)
            seen_urls.add(item["url"])
    return combined


class AgentState(BaseModel):
    """Represent the current state of the LangGraph Multi-Agent lead research workflow."""
    
    # Target brand info
    brand: Brand = Field(..., description="The D2C brand being researched.")
    
    # Traversal & scraping progress
    urls_to_visit: List[str] = Field(
        default_factory=list, 
        description="Queue of URLs discovered and scheduled for scraping."
    )
    visited_urls: List[str] = Field(
        default_factory=list, 
        description="List of URLs already scraped or visited."
    )
    
    # Scraped data cache
    scraped_pages: Annotated[List[Dict], merge_scraped_pages] = Field(
        default_factory=list,
        description="Structured content of pages scraped (e.g. {'url': str, 'html': str, 'text': str})."
    )
    
    # Accumulated contact information
    contact_info: ContactInfo = Field(
        default_factory=lambda: ContactInfo(), 
        description="Contact information collected so far."
    )
    
    # Research logs/notes accumulated across agent nodes
    logs: Annotated[List[str], merge_logs] = Field(
        default_factory=list, 
        description="Execution logs and reasoning thoughts from each agent node."
    )
    
    # Controls the flow/next step in graph
    next_step: Optional[str] = Field(
        None, 
        description="Explicit directive for the next node/action to trigger."
    )
