import re
from typing import Dict, List, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import trafilatura
from loguru import logger
from playwright.sync_api import sync_playwright

from services.interfaces.scraper import IScraperService, IWebsiteResearchService
from schemas.scraper_schemas import WebsiteResearchResult
from config.settings import settings


class WebScraperService(IScraperService):
    """Concrete implementation of IScraperService utilizing Playwright, bs4, and trafilatura."""

    def __init__(self) -> None:
        self.headless = settings.BROWSER_HEADLESS
        self.timeout = settings.BROWSER_TIMEOUT_MS
        logger.info(f"Initializing WebScraperService (headless={self.headless}, timeout={self.timeout}ms).")

    def scrape_url(self, url: str) -> Dict[str, str]:
        """Scrapes a single webpage using Playwright and extracts text and raw HTML."""
        logger.info(f"Scraping single URL: {url}")
        result = {
            "url": url,
            "raw_html": "",
            "clean_text": "",
            "title": ""
        }
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                # Wait for network idle or load
                page.goto(url, timeout=self.timeout, wait_until="load")
                result["raw_html"] = page.content()
                result["title"] = page.title()
                browser.close()
                
            # Extract clean main text using trafilatura
            result["clean_text"] = trafilatura.extract(result["raw_html"]) or ""
            
        except Exception as e:
            logger.error(f"Failed scraping page {url}: {e}")
            
        return result


class WebsiteResearchService(IWebsiteResearchService):
    """Concrete implementation of IWebsiteResearchService performing structured multi-page crawling and info extraction."""

    def __init__(self) -> None:
        self.headless = settings.BROWSER_HEADLESS
        self.timeout = settings.BROWSER_TIMEOUT_MS
        # Respectful crawling limits
        self.max_pages = 8
        logger.info(f"Initializing WebsiteResearchService (max_pages={self.max_pages}).")

    def research_website(self, homepage_url: str) -> WebsiteResearchResult:
        """Crawl the website up to max_pages and parse out contact details."""
        logger.info(f"Starting deep website research crawl for: {homepage_url}")
        
        parsed_home = urlparse(homepage_url)
        target_domain = parsed_home.netloc.lower()
        if target_domain.startswith("www."):
            target_domain = target_domain[4:]
            
        visited_urls: Set[str] = set()
        urls_to_visit: List[str] = [homepage_url]
        
        # Accumulator structures
        emails_found: Set[str] = set()
        phones_found: Set[str] = set()
        whatsapp_found: Set[str] = set()
        addresses_found: Set[str] = set()
        socials_found: Dict[str, str] = {}
        contact_page_url: Optional[str] = None
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                while urls_to_visit and len(visited_urls) < self.max_pages:
                    current_url = urls_to_visit.pop(0)
                    if current_url in visited_urls:
                        continue
                        
                    logger.info(f"Crawling ({len(visited_urls) + 1}/{self.max_pages}): {current_url}")
                    visited_urls.add(current_url)
                    
                    try:
                        page.goto(current_url, timeout=self.timeout, wait_until="load")
                        html = page.content()
                        
                        # Parse page structure
                        soup = BeautifulSoup(html, "html.parser")
                        text_content = page.locator("body").inner_text() or ""
                        
                        # 1. Check if this is a contact page (if not already set)
                        if not contact_page_url and self._is_contact_page(current_url, soup):
                            contact_page_url = current_url
                            logger.info(f"Identified contact page: {contact_page_url}")
                            
                        # 2. Extract contact details from text content
                        self._extract_emails(text_content, emails_found)
                        self._extract_phones(text_content, phones_found)
                        self._extract_addresses(soup, text_content, addresses_found)
                        
                        # 3. Extract socials, whatsapp, and new links from hrefs
                        new_links = self._parse_hrefs(
                            soup, 
                            current_url, 
                            target_domain, 
                            whatsapp_found, 
                            socials_found
                        )
                        
                        # 4. Queue discovered internal links
                        for link in new_links:
                            if link not in visited_urls and link not in urls_to_visit:
                                # Prioritize contact/about pages by adding them to the front
                                if self._is_priority_path(link):
                                    urls_to_visit.insert(0, link)
                                else:
                                    urls_to_visit.append(link)
                                    
                    except Exception as page_err:
                        logger.error(f"Error crawling page {current_url}: {page_err}")
                        
                browser.close()
                
        except Exception as e:
            logger.error(f"Failed to complete website crawl on {homepage_url}: {e}")

        return WebsiteResearchResult(
            emails=sorted(list(emails_found)),
            phones=sorted(list(phones_found)),
            whatsapp_numbers=sorted(list(whatsapp_found)),
            postal_addresses=sorted(list(addresses_found)),
            social_links=socials_found,
            contact_page_url=contact_page_url,
            visited_urls=sorted(list(visited_urls))
        )

    def _is_contact_page(self, url: str, soup: BeautifulSoup) -> bool:
        """Heuristic check to identify if a page is a Contact/Support page."""
        url_lower = url.lower()
        if any(keyword in url_lower for keyword in ["contact", "support", "get-in-touch", "help"]):
            return True
            
        # Check document title
        title = soup.title.string.lower() if soup.title else ""
        if any(keyword in title for keyword in ["contact", "support", "get-in-touch", "help"]):
            return True
            
        return False

    def _is_priority_path(self, url: str) -> bool:
        """Prioritize queuing page URLs that typically contain contact details."""
        url_lower = url.lower()
        priority_keywords = ["contact", "about", "support", "help", "faq", "terms", "privacy", "returns", "shipping"]
        return any(keyword in url_lower for keyword in priority_keywords)

    def _extract_emails(self, text: str, email_set: Set[str]) -> None:
        """Regex extract emails, filtering out common static asset false positives."""
        raw_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', text)
        for email in raw_emails:
            email_lower = email.lower()
            # Filter typical image/asset extensions that match email pattern (e.g. user@2x.png)
            if not any(email_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]):
                email_set.add(email)

    def _extract_phones(self, text: str, phone_set: Set[str]) -> None:
        """Regex extract phone numbers conforming to common formats."""
        # Match standard phone shapes: e.g. +1-555-123-4567, 1-800-800-8000, +44 20 7946 0192, (555) 123-4567
        patterns = [
            r'\+?\d{1,4}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
            r'\b1[-.]?\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US Toll-Free 1-800
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                # Basic cleaning: strip spaces/dashes and verify length
                digits_only = re.sub(r'\D', '', m)
                # Avoid capturing random small numbers or dates (e.g. 2026-07-10)
                if 9 <= len(digits_only) <= 15:
                    phone_set.add(m.strip())

    def _extract_addresses(self, soup: BeautifulSoup, text: str, address_set: Set[str]) -> None:
        """Heuristic extract physical/postal addresses from typical page DOM locations."""
        # 1. Check HTML5 <address> tag
        for addr in soup.find_all("address"):
            addr_text = addr.get_text(separator=" ").strip()
            if addr_text and len(addr_text) > 10:
                address_set.add(re.sub(r'\s+', ' ', addr_text))
                
        # 2. Heuristics parser on text blocks containing ZIP/Postal code and address clues
        # Match blocks containing US ZIP or UK/Canadian Postcodes, with keywords Rd/St/Ave/Suite/etc.
        clues = ["street", "st.", "road", "rd.", "avenue", "ave.", "suite", "ste.", "boulevard", "blvd", "hq", "headquarters", "p.o. box", "po box"]
        zip_pattern = r'\b\d{5}(?:-\d{4})?\b'  # US Zip Code
        
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            line_lower = line.lower()
            if any(clue in line_lower for clue in clues):
                # Ensure it's not a generic sentence and has a number or zip code
                if re.search(r'\d+', line) and len(line) < 150:
                    address_set.add(re.sub(r'\s+', ' ', line))

    def _parse_hrefs(
        self, 
        soup: BeautifulSoup, 
        current_url: str, 
        target_domain: str,
        whatsapp_set: Set[str],
        socials_dict: Dict[str, str]
    ) -> List[str]:
        """Extract links, identifying socials, whatsapp connections, and internal crawler targets."""
        internal_links = []
        
        social_domains = {
            "instagram.com": "instagram",
            "facebook.com": "facebook",
            "linkedin.com": "linkedin",
            "twitter.com": "twitter",
            "x.com": "twitter",
            "pinterest.com": "pinterest",
            "youtube.com": "youtube",
            "tiktok.com": "tiktok"
        }
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
                
            absolute_url = urljoin(current_url, href)
            parsed_url = urlparse(absolute_url)
            domain = parsed_url.netloc.lower()
            
            # 1. WhatsApp Detect
            if "wa.me/" in absolute_url or "api.whatsapp.com/send" in absolute_url:
                # Try to extract the phone number from whatsapp link
                phone_match = re.search(r'(?:phone=|wa\.me/)(\d+)', absolute_url)
                if phone_match:
                    whatsapp_set.add(phone_match.group(1))
                else:
                    whatsapp_set.add(absolute_url)
                continue
                
            # 2. Social Links Detect
            is_social = False
            for soc_dom, platform in social_domains.items():
                if soc_dom in domain:
                    # Filter out share buttons
                    if not any(ignored in absolute_url for ignored in ["/sharer", "/share", "/intent/tweet"]):
                        socials_dict[platform] = absolute_url
                    is_social = True
                    break
                    
            if is_social:
                continue
                
            # 3. Internal Crawler Target Filter
            # Check if domain matches targeted domain
            clean_domain = domain[4:] if domain.startswith("www.") else domain
            if clean_domain == target_domain:
                # Avoid non-HTML formats
                if not any(parsed_url.path.lower().endswith(ext) for ext in [".pdf", ".zip", ".jpg", ".png", ".jpeg", ".mp4"]):
                    # Strip query parameters/fragments to avoid duplicate pages
                    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                    internal_links.append(clean_url)
                    
        return internal_links
