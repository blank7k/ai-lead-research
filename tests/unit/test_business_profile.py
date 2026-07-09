from unittest.mock import MagicMock, patch
import pytest

from models.domain import Lead, Contacts, Socials
from services.business_profile_service import DuckDuckGoBusinessProfileProvider
from tools.registry import BusinessProfileTool


@pytest.fixture
def mock_search_hits():
    return [
        {
            "title": "Nike - Portland OR - Google Maps",
            "body": "Nike rating is 4.6 out of 5 based on 320 reviews. HQ office address: One Bowerman Dr, Beaverton, OR 97005. Contact number: +1 503-671-6453. Open ⋅ Closes 6 PM.",
            "href": "https://google.com/maps/place/Nike"
        },
        {
            "title": "Nike Headquarters Contact Details",
            "body": "Call Nike headquarters at 1-503-671-6453 or visit them at Beaverton, OR.",
            "href": "https://nike.com"
        }
    ]


def test_business_profile_provider_extraction(mock_search_hits):
    """Verify that DuckDuckGoBusinessProfileProvider extracts expected fields from search snippets."""
    mock_search = MagicMock()
    mock_search.search.return_value = mock_search_hits
    
    provider = DuckDuckGoBusinessProfileProvider(search_service=mock_search)
    profile = provider.fetch_profile("Nike")
    
    assert profile["phone"] == "+1 503-671-6453"
    assert "Beaverton, OR 97005" in profile["address"]
    assert profile["google_maps_url"] == "https://google.com/maps/place/Nike"
    assert profile["rating"] == 4.6
    assert profile["review_count"] == 320
    assert "Closes 6 PM" in profile["opening_hours"]


def test_business_profile_tool_merging(mock_search_hits):
    """Verify that BusinessProfileTool correctly merges newly discovered details into Lead."""
    mock_search = MagicMock()
    mock_search.search.return_value = mock_search_hits
    
    provider = DuckDuckGoBusinessProfileProvider(search_service=mock_search)
    
    lead = Lead(brand_name="Nike")
    assert lead.confidence_score == 0.0
    
    # Execute tool with patched provider
    tool = BusinessProfileTool()
    with patch("tools.registry.DuckDuckGoBusinessProfileProvider", return_value=provider):
        updated_lead, trace = tool.execute(lead)
        
    assert "+1 503-671-6453" in updated_lead.contacts.phones
    assert "One Bowerman Dr" in updated_lead.contacts.addresses[0]
    assert updated_lead.socials.google_maps == "https://google.com/maps/place/Nike"
    assert updated_lead.enrichments["rating"] == 4.6
    assert updated_lead.enrichments["review_count"] == 320
    assert updated_lead.confidence_score > 0.0
    
    # Assert trace content
    assert "✓ Phone Found" in trace
    assert "✓ Address Found" in trace
    assert "✓ Maps Link Found" in trace


def test_business_profile_tool_no_duplicates():
    """Verify that tool execution does not result in duplicate contact info or confidence bumps."""
    tool = BusinessProfileTool()
    
    lead = Lead(brand_name="Nike")
    lead.contacts.phones = ["+1 503-671-6453"]
    lead.contacts.addresses = ["One Bowerman Dr, Beaverton, OR 97005"]
    lead.socials.google_maps = "https://google.com/maps/place/Nike"
    lead.enrichments = {"rating": 4.6, "review_count": 320, "opening_hours": "Open ⋅ Closes 6 PM"}
    lead.confidence_score = 0.5
    
    # Mock provider returning same details
    mock_profile = {
        "phone": "+1 503-671-6453",
        "address": "One Bowerman Dr, Beaverton, OR 97005",
        "google_maps_url": "https://google.com/maps/place/Nike",
        "rating": 4.6,
        "review_count": 320,
        "opening_hours": "Open ⋅ Closes 6 PM"
    }
    
    mock_provider = MagicMock()
    mock_provider.fetch_profile.return_value = mock_profile
    
    with patch("tools.registry.DuckDuckGoBusinessProfileProvider", return_value=mock_provider):
        updated_lead, trace = tool.execute(lead)
        
    # Phone, Address, Maps should not have duplicate items or updated score
    assert len(updated_lead.contacts.phones) == 1
    assert len(updated_lead.contacts.addresses) == 1
    assert updated_lead.confidence_score == 0.5 # Unchanged as no new details were found
