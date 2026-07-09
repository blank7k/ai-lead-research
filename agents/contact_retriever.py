from loguru import logger
from schemas.agent_state import AgentState
from models.domain import ContactInfo


def contact_retriever_node(state: AgentState) -> dict:
    """
    Agent node that processes scheduled subpages to retrieve emails, phone numbers,
    and social media URLs.
    
    Args:
        state: The current LangGraph workflow state.
        
    Returns:
        State updates containing extracted ContactInfo and logs.
    """
    brand = state.brand
    logger.info(f"[Contact Retriever] Scraping candidate URLs for brand: {brand.name}")
    
    # Placeholder node execution logic:
    # 1. Take URLs from state.urls_to_visit.
    # 2. Call scraper_service on those URLs.
    # 3. Use an LLM or regular expressions to pull contact details from scraped text.
    # 4. Save into updated ContactInfo.
    
    extracted_contact_info = ContactInfo(
        emails=["info@example.com"], # Mock email placeholder
        phones=["+1-555-0199"],
        instagram_url=f"https://instagram.com/{brand.domain.split('.')[0]}",
        contact_page_url=f"{brand.website_url.rstrip('/')}/contact",
        raw_sources=[f"{brand.website_url.rstrip('/')}/contact"]
    )
    
    log_entry = f"Contact Retriever: Extracted emails and social profiles from contact page."
    
    return {
        "contact_info": extracted_contact_info,
        "visited_urls": state.urls_to_visit, # Mark all as visited
        "urls_to_visit": [], # Clear queue
        "logs": [log_entry],
        "next_step": "end"
    }
