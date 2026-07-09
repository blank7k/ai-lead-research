from abc import ABC, abstractmethod
from typing import Dict


class IScraperService(ABC):
    """Clean architecture interface for web scraping (using Playwright, BeautifulSoup4, Trafilatura)."""

    @abstractmethod
    def scrape_url(self, url: str) -> Dict[str, str]:
        """
        Scrape a given URL and extract clean text and metadata.
        
        Returns:
            Dict[str, str]: E.g., {'url': url, 'raw_html': ..., 'clean_text': ...}
        """
        pass
