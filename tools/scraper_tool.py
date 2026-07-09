from langchain_core.tools import tool
from services.scraper_service import WebsiteResearchService
from schemas.scraper_schemas import WebsiteResearchResult


@tool
def website_research_tool(homepage_url: str) -> str:
    """
    Crawls a brand's D2C website up to 8 pages to find contact endpoints and extract 
    public business emails, phone numbers, WhatsApp links, physical addresses, and social media pages.
    
    Args:
        homepage_url: The main home page URL of the website.
        
    Returns:
        JSON string of WebsiteResearchResult containing emails, phones, whatsapp_numbers,
        postal_addresses, social_links, contact_page_url, and visited_urls.
    """
    crawler = WebsiteResearchService()
    result = crawler.research_website(homepage_url)
    return result.model_dump_json(indent=2)
