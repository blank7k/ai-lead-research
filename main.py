import sys
import time
from typing import Optional, List
from urllib.parse import urlparse
from loguru import logger

from config.settings import settings
from models.domain import Brand, ContactInfo, Lead
from services.search_service import DuckDuckGoSearchProvider
from services.scraper_service import WebsiteResearchService


def extract_domain_name(url: str) -> str:
    """Helper utility to extract domain name (e.g. brand.com) from absolute URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            return domain[4:]
        return domain
    except Exception:
        return "unknown"


def calculate_confidence_score(contact: ContactInfo, has_website: bool) -> float:
    """
    Heuristics-based confidence score builder.
    Score structure (0.0 to 1.0):
    - Website found: +0.2
    - Emails found: +0.2 per unique email (max 0.4)
    - Phone number found: +0.2
    - Social profile pages linked: +0.1 per unique social platform (max 0.2)
    """
    score = 0.0
    if has_website:
        score += 0.2
    
    # Emails
    if contact.emails:
        score += min(len(contact.emails) * 0.2, 0.4)
        
    # Phones
    if contact.phones:
        score += 0.2
        
    # Social channels
    socials_count = 0
    if contact.instagram_url: socials_count += 1
    if contact.facebook_url: socials_count += 1
    if contact.linkedin_url: socials_count += 1
    if contact.twitter_url: socials_count += 1
    
    score += min(socials_count * 0.1, 0.2)
    
    return round(score, 2)


def run_lead_research_pipeline(brand_name: str) -> Optional[Lead]:
    """
    Executes the multi-agent research pipeline for a given brand name.
    Chains Search and Crawling, then builds a consolidated Lead entity.
    """
    logger.info(f"=== Starting pipeline research for brand: '{brand_name}' ===")
    
    # 1. Search Tool execution
    search_provider = DuckDuckGoSearchProvider()
    search_result = search_provider.search_brand(brand_name)
    
    website_url = search_result.official_website
    
    # If no website is found, we handle it gracefully by building a partial Lead
    if not website_url:
        logger.warning(f"Pipeline: Could not resolve official website URL for '{brand_name}'. Crawl skipped.")
        
        brand = Brand(
            name=brand_name,
            website_url="unknown",
            domain="unknown"
        )
        contact_info = ContactInfo(
            instagram_url=search_result.instagram_url,
            facebook_url=search_result.facebook_url,
            linkedin_url=search_result.linkedin_url,
            raw_sources=[r.get("href", "") for r in search_result.raw_results[:3] if r.get("href")]
        )
        
        return Lead(
            brand=brand,
            contact_info=contact_info,
            is_verified=False,
            confidence_score=calculate_confidence_score(contact_info, has_website=False),
            research_notes="Pipeline execution completed. Searching returned social channels but website resolution failed."
        )
        
    # 2. Website research/crawler tool execution
    logger.info(f"Pipeline: Resolving details from website crawler at {website_url}...")
    scraper = WebsiteResearchService()
    crawl_result = scraper.research_website(website_url)
    
    # 3. Consolidate outputs
    brand = Brand(
        name=brand_name,
        website_url=website_url,
        domain=extract_domain_name(website_url)
    )
    
    # Prefer crawler-extracted socials, fallback to search-extracted socials
    contact_info = ContactInfo(
        emails=crawl_result.emails,
        phones=crawl_result.phones,
        instagram_url=crawl_result.social_links.get("instagram") or search_result.instagram_url,
        facebook_url=crawl_result.social_links.get("facebook") or search_result.facebook_url,
        linkedin_url=crawl_result.social_links.get("linkedin") or search_result.linkedin_url,
        twitter_url=crawl_result.social_links.get("twitter") or crawl_result.social_links.get("x"),
        contact_page_url=crawl_result.contact_page_url,
        physical_address=crawl_result.postal_addresses[0] if crawl_result.postal_addresses else None,
        raw_sources=crawl_result.visited_urls
    )
    
    is_verified = len(contact_info.emails) > 0
    confidence = calculate_confidence_score(contact_info, has_website=True)
    
    lead = Lead(
        brand=brand,
        contact_info=contact_info,
        is_verified=is_verified,
        confidence_score=confidence,
        research_notes=f"Pipeline execution completed successfully. Crawled {len(crawl_result.visited_urls)} pages."
    )
    
    logger.info(f"=== Completed pipeline research for brand: '{brand_name}' (Confidence: {confidence}) ===")
    return lead


def main():
    """Main CLI entry point."""
    # Determine targets
    args = sys.argv[1:]
    if args:
        targets = args
    else:
        # Default D2C brands requested by the user
        targets = ["ROSANI", "Perte D'ego", "POMCHA"]
        
    logger.info(f"Initializing Lead Research Pipeline for targets: {targets}")
    
    results = []
    for idx, brand_name in enumerate(targets):
        if idx > 0:
            logger.info("Throttling request. Sleeping for 5 seconds to prevent rate limiting...")
            time.sleep(5)
            
        try:
            lead = run_lead_research_pipeline(brand_name)
            if lead:
                results.append(lead)
                print("\n" + "="*50)
                print(f"RESEARCH RESULT FOR: {brand_name.upper()}")
                print("="*50)
                print(lead.model_dump_json(indent=2))
                print("="*50 + "\n")
        except Exception as e:
            logger.error(f"Failed to process brand '{brand_name}': {e}")
            
    logger.info("Lead Research Pipeline execution completed.")


if __name__ == "__main__":
    main()
