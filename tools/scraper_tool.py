from langchain_core.tools import tool
from services.scraper_service import WebScraperService


@tool
def page_scraper_tool(url: str) -> str:
    """
    Scrapes the raw text and metadata of a specific webpage URL.
    Useful for extracting contact information, emails, about-us statements, and phone numbers from pages.
    
    Args:
        url: The absolute HTTP/HTTPS URL of the page to scrape.
        
    Returns:
        The extracted main text content of the page.
    """
    scraper = WebScraperService()
    scraped_data = scraper.scrape_url(url)
    clean_text = scraped_data.get("clean_text") or ""
    
    if not clean_text:
        return f"Scraping completed, but no readable text could be extracted from: {url}"
        
    # Cap text output length to prevent overloading context window
    max_chars = 8000
    if len(clean_text) > max_chars:
        return clean_text[:max_chars] + "\n... [Content Truncated due to length] ..."
        
    return clean_text
