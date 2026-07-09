from langchain_core.tools import tool
from services.search_service import DuckDuckGoSearchProvider
from schemas.search_schemas import BrandSearchResult


@tool
def brand_search_tool(brand_name: str) -> str:
    """
    Search the web for a brand name to find its official website, social media pages, and Google Maps info.
    
    Args:
        brand_name: The name of the D2C brand to research.
        
    Returns:
        JSON string of BrandSearchResult containing official_website, instagram_url, 
        facebook_url, linkedin_url, and google_maps_url.
    """
    provider = DuckDuckGoSearchProvider()
    result = provider.search_brand(brand_name)
    return result.model_dump_json(indent=2)
