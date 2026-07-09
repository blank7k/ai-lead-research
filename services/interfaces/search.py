from abc import ABC, abstractmethod
from typing import List, Dict
from schemas.search_schemas import BrandSearchResult


class ISearchService(ABC):
    """Clean architecture interface for raw web search queries."""

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Execute a search query and return formatted results.
        
        Returns:
            List[Dict[str, str]]: E.g., [{'title': ..., 'url': ..., 'snippet': ...}]
        """
        pass


class ISearchProvider(ABC):
    """Provider-agnostic interface for executing structured brand research searches."""

    @abstractmethod
    def search_brand(self, brand_name: str) -> BrandSearchResult:
        """
        Search for a brand by name and extract structured URLs (website, socials, maps).
        
        Args:
            brand_name: Name of the brand (e.g. "Gymshark", "Zara").
            
        Returns:
            BrandSearchResult containing parsed profile links and raw search records.
        """
        pass
