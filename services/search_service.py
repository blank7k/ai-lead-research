from typing import List, Dict, Optional
from urllib.parse import urlparse
from loguru import logger
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

from services.interfaces.search import ISearchService, ISearchProvider
from schemas.search_schemas import BrandSearchResult
from config.settings import settings


class DuckDuckGoSearchService(ISearchService):
    """Concrete implementation of ISearchService using the duckduckgo-search library."""

    def __init__(self) -> None:
        self.max_results = settings.MAX_SEARCH_RESULTS
        logger.info("Initializing DuckDuckGo Search Service.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def search(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Execute raw text search on DuckDuckGo using retry logic.
        Uses the 'lite' HTML backend for reliability under heavy automation.
        """
        limit = max_results or self.max_results
        logger.info(f"Executing raw DuckDuckGo search for query: '{query}' (limit={limit})")
        
        try:
            with DDGS() as ddgs:
                # We use backend="lite" as it is less prone to automated scraper blocks
                results = ddgs.text(query, backend="lite", max_results=limit)
                if not results:
                    logger.warning(f"DuckDuckGo returned empty results for: '{query}'")
                    raise Exception("Empty results returned, possible temporary rate limit or block")
                
                # Standardize return fields: link/url -> href, snippet/body -> body
                formatted_results = []
                for r in results:
                    formatted_results.append({
                        "title": r.get("title") or "",
                        "href": r.get("href") or r.get("url") or "",
                        "body": r.get("body") or r.get("snippet") or ""
                    })
                logger.debug(f"Retrieved {len(formatted_results)} results for query: '{query}'")
                return formatted_results
        except Exception as e:
            logger.error(f"Error during DuckDuckGo search query '{query}': {e}")
            raise e


class DuckDuckGoSearchProvider(ISearchProvider):
    """Concrete implementation of ISearchProvider executing brand search and heuristics-based parsing."""

    def __init__(self, search_service: Optional[ISearchService] = None) -> None:
        self.search_service = search_service or DuckDuckGoSearchService()
        logger.info("Initializing DuckDuckGo Search Provider.")

    def search_brand(self, brand_name: str) -> BrandSearchResult:
        """
        Search for a brand by name and extract structured URLs (website, socials, maps).
        """
        logger.info(f"Initiating brand search research for: '{brand_name}'")
        
        # Clean brand name of quotes which trigger search anomalies / rate-limiting blocks
        clean_name = brand_name.replace("'", "").replace('"', "").strip()
        
        # Build search query optimized to surface home page and social links
        query = f"{clean_name} clothing fashion brand website"
        
        # Fetch search results with slightly higher limit to catch social accounts on page 1
        raw_hits = []
        try:
            raw_hits = self.search_service.search(query, max_results=15)
            if not raw_hits:
                logger.warning(f"Primary search for '{brand_name}' returned zero hits. Retrying with fallback query...")
                raw_hits = self.search_service.search(f"{clean_name} clothing", max_results=10)
        except Exception as e:
            logger.error(f"Search provider failed to execute search for '{brand_name}': {e}")
            # Return empty result shell instead of crashing
            return BrandSearchResult(brand_name=brand_name, raw_results=[])
            
        return self._parse_results(brand_name, raw_hits)

    def _parse_results(self, brand_name: str, results: List[Dict[str, str]]) -> BrandSearchResult:
        """Parse raw search hits to extract target business endpoints."""
        official_website = None
        instagram_url = None
        facebook_url = None
        linkedin_url = None
        google_maps_url = None
        
        # Domains to filter out when seeking the official D2C brand website
        excluded_domains = {
            "instagram.com", "facebook.com", "linkedin.com", "twitter.com", "x.com",
            "pinterest.com", "youtube.com", "tiktok.com", "wikipedia.org", "amazon.com",
            "yelp.com", "tripadvisor.com", "glassdoor.com", "indeed.com", "google.com",
            "maps.google.com", "apple.com", "play.google.com", "crunchbase.com",
            "reddit.com", "shopify.com", "etsy.com", "ebay.com"
        }
        
        for r in results:
            url = r.get("href") or r.get("url") or ""
            if not url:
                continue
                
            url_lower = url.lower()
            
            # Extract social links and other platforms based on pattern matches
            if "instagram.com/" in url_lower and not instagram_url:
                if not any(ignored in url_lower for ignored in ["/p/", "/reel/", "/explore/", "/developer"]):
                    instagram_url = url
                    logger.debug(f"Found Instagram URL: {url}")
                    
            elif "facebook.com/" in url_lower and not facebook_url:
                if not any(ignored in url_lower for ignored in ["/sharer", "/pages/category", "/groups", "/events"]):
                    facebook_url = url
                    logger.debug(f"Found Facebook URL: {url}")
                    
            elif "linkedin.com/" in url_lower and not linkedin_url:
                if "linkedin.com/company/" in url_lower or "linkedin.com/in/" in url_lower:
                    linkedin_url = url
                    logger.debug(f"Found LinkedIn URL: {url}")
                    
            elif ("google.com/maps" in url_lower or "maps.google.com" in url_lower or "maps.app.goo.gl" in url_lower) and not google_maps_url:
                google_maps_url = url
                logger.debug(f"Found Google Maps URL: {url}")
                
            elif not official_website:
                # Heuristic: First URL that belongs to a protocol scheme and is not excluded
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                        
                    is_excluded = False
                    for excl in excluded_domains:
                        if domain == excl or domain.endswith("." + excl):
                            is_excluded = True
                            break
                            
                    if not is_excluded and parsed.scheme in ["http", "https"]:
                        # Extract root URL (protocol + netloc)
                        official_website = f"{parsed.scheme}://{parsed.netloc}"
                        logger.info(f"Identified official brand website: {official_website}")
                except Exception as e:
                    logger.warning(f"Error parsing URL '{url}' for brand website heuristic: {e}")
                    
        return BrandSearchResult(
            brand_name=brand_name,
            official_website=official_website,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            linkedin_url=linkedin_url,
            google_maps_url=google_maps_url,
            raw_results=results
        )
