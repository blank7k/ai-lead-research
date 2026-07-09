from unittest.mock import MagicMock, patch
import pytest
from services.search_service import DuckDuckGoSearchProvider, DuckDuckGoSearchService
from schemas.search_schemas import BrandSearchResult


def test_duckduckgo_search_provider_parsing():
    """Verify that search provider parses social media, website, and maps URLs correctly."""
    # Arrange
    mock_service = MagicMock()
    mock_service.search.return_value = [
        {"title": "Zara Official Website", "href": "https://www.zara.com/us/en", "body": "Zara homepage"},
        {"title": "Zara Instagram", "href": "https://instagram.com/zara", "body": "Zara Instagram profile"},
        {"title": "Zara Facebook", "href": "https://facebook.com/zara", "body": "Zara Facebook page"},
        {"title": "Zara LinkedIn", "href": "https://linkedin.com/company/zara", "body": "Zara LinkedIn company page"},
        {"title": "Zara Google Maps Store Location", "href": "https://www.google.com/maps/place/Zara", "body": "Zara maps listing"}
    ]
    
    provider = DuckDuckGoSearchProvider(search_service=mock_service)
    
    # Act
    result = provider.search_brand("Zara")
    
    # Assert
    assert result.brand_name == "Zara"
    assert result.official_website == "https://www.zara.com"
    assert result.instagram_url == "https://instagram.com/zara/us/en" or result.instagram_url == "https://instagram.com/zara"
    assert result.facebook_url == "https://facebook.com/zara"
    assert result.linkedin_url == "https://linkedin.com/company/zara"
    assert result.google_maps_url == "https://www.google.com/maps/place/Zara"


def test_duckduckgo_search_provider_website_heuristics():
    """Verify website heuristics exclude common aggregator/social domains and parse root URLs."""
    # Arrange
    mock_service = MagicMock()
    mock_service.search.return_value = [
        {"title": "Zara Instagram", "href": "https://instagram.com/zara", "body": "Instagram"},
        {"title": "Zara Amazon Shop", "href": "https://www.amazon.com/Zara", "body": "Amazon shop"},
        {"title": "Zara Home", "href": "https://www.zara.com/us/en", "body": "Actual website"}
    ]
    
    provider = DuckDuckGoSearchProvider(search_service=mock_service)
    
    # Act
    result = provider.search_brand("Zara")
    
    # Assert
    assert result.official_website == "https://www.zara.com"
    assert result.instagram_url == "https://instagram.com/zara"


def test_duckduckgo_search_provider_exception_handling():
    """Verify that search provider returns an empty result model on search failure instead of crashing."""
    # Arrange
    mock_service = MagicMock()
    mock_service.search.side_effect = Exception("Service unavailable")
    provider = DuckDuckGoSearchProvider(search_service=mock_service)
    
    # Act
    result = provider.search_brand(" Zara ")
    
    # Assert
    assert result.brand_name == " Zara "
    assert result.official_website is None
    assert len(result.raw_results) == 0


def test_duckduckgo_search_service_retry():
    """Verify that search service retries on exceptions and succeeds if subsequent calls work."""
    # Arrange
    with patch("services.search_service.DDGS") as mock_ddgs_class:
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__.return_value = mock_ddgs
        
        # Fail twice, succeed on third attempt
        mock_ddgs.text.side_effect = [
            Exception("Rate limit warning"),
            Exception("Timeout error"),
            [{"title": "Success Site", "href": "https://success.com", "body": "Works now"}]
        ]
        
        service = DuckDuckGoSearchService()
        
        # Bypass sleeping delay in tenacity during test runs
        with patch("tenacity.nap.sleep", return_value=None):
            results = service.search("success brand")
            
        # Assert
        assert len(results) == 1
        assert results[0]["href"] == "https://success.com"
        assert mock_ddgs.text.call_count == 3
