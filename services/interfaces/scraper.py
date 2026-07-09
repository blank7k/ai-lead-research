from abc import ABC, abstractmethod
from typing import Dict
from schemas.scraper_schemas import WebsiteResearchResult


class IScraperService(ABC):
    """Clean architecture interface for raw, single URL web scraping."""

    @abstractmethod
    def scrape_url(self, url: str) -> Dict[str, str]:
        """
        Scrape a given URL and extract clean text and metadata.
        
        Returns:
            Dict[str, str]: E.g., {'url': url, 'raw_html': ..., 'clean_text': ...}
        """
        pass


class IWebsiteResearchService(ABC):
    """Clean architecture interface for full-site crawling and contact extraction."""

    @abstractmethod
    def research_website(self, homepage_url: str) -> WebsiteResearchResult:
        """
        Crawl internal pages of a website to extract structured business contact info.
        
        Args:
            homepage_url: The main home page URL of the D2C brand.
            
        Returns:
            WebsiteResearchResult containing found emails, phones, addresses, and social links.
        """
        pass
