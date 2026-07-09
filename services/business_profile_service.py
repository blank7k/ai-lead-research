import re
from typing import Optional, List, Dict
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from services.interfaces.business_profile import IBusinessProfileProvider
from services.search_service import DuckDuckGoSearchService


class DuckDuckGoBusinessProfileProvider(IBusinessProfileProvider):
    """
    Concrete Business Profile Provider executing DuckDuckGo search queries
    and extracting contact details, ratings, reviews, and address info.
    """

    def __init__(self, search_service: Optional[DuckDuckGoSearchService] = None) -> None:
        self.search_service = search_service or DuckDuckGoSearchService()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _execute_query_with_retry(self, query: str) -> List[Dict]:
        """Executes a search query with retry logic to handle rate-limiting."""
        return self.search_service.search(query, max_results=5)

    def fetch_profile(self, brand_name: str) -> dict:
        logger.info(f"[DuckDuckGoBusinessProfileProvider] Gathering business profile for '{brand_name}'...")
        
        # Clean brand name of quotes
        clean_name = brand_name.replace("'", "").replace('"', "").strip()
        
        # Target search queries to extract maps info
        queries = [
            f"{clean_name} google maps locations",
            f"{clean_name} headquarters contact address phone",
            f"{clean_name} business rating hours",
            f"{clean_name} address contact"
        ]
        
        all_hits = []
        for q in queries:
            try:
                hits = self._execute_query_with_retry(q)
                if hits:
                    all_hits.extend(hits)
            except Exception as e:
                logger.warning(f"Query '{q}' failed: {e}")
                
        # Parse fields from the consolidated hits
        profile = {
            "phone": None,
            "address": None,
            "website": None,
            "google_maps_url": None,
            "rating": None,
            "review_count": None,
            "opening_hours": None
        }
        
        # Keep track of parsed lists to choose the best/most frequent matches
        phones = []
        addresses = []
        maps_urls = []
        ratings = []
        reviews = []
        hours_list = []
        websites = []
        
        # Standard Phone regex pattern (handles country codes, spaces, dashes)
        # e.g., +91 81074 92018, 1-800-806-6453
        phone_pattern = re.compile(
            r'(?:\+?[1-9]\d{0,3}[-.\s]*)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        )
        
        # Rating extraction patterns
        rating_patterns = [
            re.compile(r'Rating:?\s*([1-5](?:\.\d+)?)'),
            re.compile(r'([1-5](?:\.\d+)?)\s*(?:out of 5|stars|/5|\u2605|\u2b50)'),
        ]
        
        # Review extraction patterns
        review_patterns = [
            re.compile(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(?:reviews|votes|ratings)'),
            re.compile(r'\(([^)]+)\)\s*(?:Google Reviews|reviews)')
        ]
        
        # Address identifier phrases / markers
        address_markers = [
            r'Flat No\.\s*\d+[^,]+,[^,]+',
            r'Plot No\.\s*\d+[^,]+,[^,]+',
            r'\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Highway|Hwy|Boulevard|Blvd|Suite|Floor|Building|Phase|Industrial Area|West|East|North|South)[^,.]*',
            r'(?:HQ|Headquarters|Address|Office):\s*([^.]+)'
        ]
        address_patterns = [re.compile(marker, re.IGNORECASE) for marker in address_markers]

        # Opening hours patterns
        hours_patterns = [
            re.compile(r'(?:Open|Closed)\s*(?:\u22c5|\u2022|\u00b7)\s*(?:Opens|Closes)\s*[^.\n]+', re.IGNORECASE),
            re.compile(r'Hours:\s*([^.\n]+)', re.IGNORECASE),
            re.compile(r'(?:Mon-Fri|Monday-Friday|Open 24 hours)', re.IGNORECASE)
        ]

        for hit in all_hits:
            title = hit.get("title", "")
            snippet = hit.get("body", "")
            url = hit.get("href", "")
            
            combined_text = f"{title} | {snippet}"
            
            # 1. Maps URL
            if "google.com/maps" in url or "maps.google.com" in url or "maps.app.goo.gl" in url:
                maps_urls.append(url)
                
            # 2. Phone numbers
            for match in phone_pattern.finditer(combined_text):
                num = match.group(0).strip()
                # Ignore numbers that look like dates/years (e.g. 2026 0000)
                if len(re.sub(r'\D', '', num)) >= 7:
                    phones.append(num)
                    
            # 3. Ratings
            for pat in rating_patterns:
                match = pat.search(combined_text)
                if match:
                    try:
                        ratings.append(float(match.group(1)))
                    except ValueError:
                        pass
                        
            # 4. Review Counts
            for pat in review_patterns:
                match = pat.search(combined_text)
                if match:
                    try:
                        clean_num = match.group(1).replace(",", "")
                        reviews.append(int(clean_num))
                    except ValueError:
                        pass
                        
            # 5. Addresses
            for pat in address_patterns:
                match = pat.search(combined_text)
                if match:
                    addr = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    addr_cleaned = addr.strip().strip(":").strip()
                    if len(addr_cleaned) > 8:
                        addresses.append(addr_cleaned)

            # 6. Opening Hours
            for pat in hours_patterns:
                match = pat.search(combined_text)
                if match:
                    hours_val = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    hours_list.append(hours_val.strip())

        # Select the best fits
        if maps_urls:
            profile["google_maps_url"] = maps_urls[0]
        if phones:
            profile["phone"] = phones[0]
        if addresses:
            profile["address"] = addresses[0]
        if ratings:
            profile["rating"] = ratings[0]
        if reviews:
            profile["review_count"] = reviews[0]
        if hours_list:
            profile["opening_hours"] = hours_list[0]
            
        logger.debug(f"[DuckDuckGoBusinessProfileProvider] Parsed attributes: {profile}")
        return profile
