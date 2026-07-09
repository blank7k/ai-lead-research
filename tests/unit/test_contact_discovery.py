"""
Unit tests for services/contact_extractor.py and tools/contact_discovery.py.
"""

from unittest.mock import MagicMock, patch
import pytest

from services.contact_extractor import extract_emails, extract_phones, clean_brand_name
from models.domain import Lead


# ---------------------------------------------------------------------------
# ContactExtractor – email
# ---------------------------------------------------------------------------

class TestExtractEmails:
    def test_plain_email(self):
        assert "hello@brand.com" in extract_emails("Contact us at hello@brand.com")

    def test_multiple_emails(self):
        text = "Email sales@brand.com or support@brand.in for help."
        found = extract_emails(text)
        assert "sales@brand.com" in found
        assert "support@brand.in" in found

    def test_filters_image_extensions(self):
        assert not extract_emails("user@2x.png is not an email")

    def test_filters_placeholder(self):
        assert not extract_emails("Send to noreply@example.com")

    def test_empty_text(self):
        assert extract_emails("") == set()

    def test_email_in_unicode_text(self):
        assert "info@रोसानी.com" not in extract_emails("check info@रोसानी.com")  # non-ASCII domain skipped by regex


# ---------------------------------------------------------------------------
# ContactExtractor – phone
# ---------------------------------------------------------------------------

class TestExtractPhones:
    def test_us_format(self):
        phones = extract_phones("Call us at +1-800-555-1234")
        assert phones  # at least one match

    def test_indian_mobile(self):
        phones = extract_phones("WhatsApp: +91 98765 43210")
        assert phones

    def test_five_plus_five(self):
        phones = extract_phones("Reach us: 98765 43210")
        assert phones

    def test_rejects_dates(self):
        # "2026" style strings should not be returned as phone numbers
        phones = extract_phones("Year 2026-07-10 is a date")
        # Any match must satisfy digit-count guard 7-15
        for p in phones:
            import re
            digits = len(re.sub(r"\D", "", p))
            assert 7 <= digits <= 15

    def test_empty_text(self):
        assert extract_phones("") == set()


# ---------------------------------------------------------------------------
# clean_brand_name
# ---------------------------------------------------------------------------

class TestCleanBrandName:
    def test_removes_apostrophe(self):
        assert "Perte Dego" == clean_brand_name("Perte D'ego")

    def test_removes_quotes(self):
        assert "Brand Name" == clean_brand_name('"Brand Name"')

    def test_no_change_on_clean(self):
        assert "ROSANI" == clean_brand_name("ROSANI")


# ---------------------------------------------------------------------------
# ContactDiscoveryTool – unit (all network calls mocked)
# ---------------------------------------------------------------------------

class TestContactDiscoveryTool:

    def _make_lead(self, website="https://testbrand.com"):
        lead = Lead(brand_name="TestBrand")
        lead.website = website
        return lead

    def test_tool_name(self):
        from tools.contact_discovery import ContactDiscoveryTool
        assert ContactDiscoveryTool().name == "contact_discovery_tool"

    def test_merges_emails_from_website_crawl(self):
        from tools.contact_discovery import ContactDiscoveryTool
        from schemas.scraper_schemas import WebsiteResearchResult

        mock_result = WebsiteResearchResult(
            emails=["info@testbrand.com"],
            phones=["+91 98765 43210"],
            whatsapp_numbers=[],
            postal_addresses=[],
            social_links={},
            contact_page_url=None,
            visited_urls=["https://testbrand.com"]
        )

        with patch("tools.contact_discovery.WebsiteResearchService") as MockCrawler:
            MockCrawler.return_value.research_website.return_value = mock_result
            # Patch search so it returns nothing (avoids network)
            with patch("tools.contact_discovery.DuckDuckGoSearchService") as MockSearch:
                MockSearch.return_value.search.return_value = []
                tool = ContactDiscoveryTool(max_queries=0, max_pages=1, max_runtime_s=30)
                lead = self._make_lead()
                updated_lead, trace = tool.execute(lead)

        assert "info@testbrand.com" in updated_lead.contacts.emails
        assert updated_lead.contacts.phones  # phone found
        assert "email_sources" in updated_lead.enrichments
        assert "phone_sources" in updated_lead.enrichments

    def test_stops_early_when_both_found(self):
        """Once email+phone are found on the website, no search queries should fire."""
        from tools.contact_discovery import ContactDiscoveryTool
        from schemas.scraper_schemas import WebsiteResearchResult

        mock_result = WebsiteResearchResult(
            emails=["hello@brand.com"],
            phones=["+1-800-555-1234"],
            whatsapp_numbers=[],
            postal_addresses=[],
            social_links={},
            contact_page_url=None,
            visited_urls=["https://testbrand.com"]
        )

        with patch("tools.contact_discovery.WebsiteResearchService") as MockCrawler, \
             patch("tools.contact_discovery.DuckDuckGoSearchService") as MockSearch:
            MockCrawler.return_value.research_website.return_value = mock_result
            tool = ContactDiscoveryTool(max_queries=5, max_pages=1, max_runtime_s=30)
            lead = self._make_lead()
            updated_lead, _ = tool.execute(lead)

            # Search should never have been called because cascade stopped early
            MockSearch.return_value.search.assert_not_called()

        assert "hello@brand.com" in updated_lead.contacts.emails

    def test_no_website_skips_crawl_but_searches(self):
        """When no website is known, the website crawl is skipped but search fires."""
        from tools.contact_discovery import ContactDiscoveryTool

        with patch("tools.contact_discovery.WebsiteResearchService") as MockCrawler, \
             patch("tools.contact_discovery.DuckDuckGoSearchService") as MockSearch:
            MockSearch.return_value.search.return_value = [
                {"href": "https://fb.com/testbrand", "body": "Email us at test@brand.com", "title": ""}
            ]
            tool = ContactDiscoveryTool(max_queries=3, max_pages=1, max_runtime_s=30)
            lead = self._make_lead(website=None)
            updated_lead, _ = tool.execute(lead)

            # Website crawl should not have been called
            MockCrawler.return_value.research_website.assert_not_called()

        assert "test@brand.com" in updated_lead.contacts.emails

    def test_deduplicates_contacts(self):
        """Same email found from multiple sources should appear only once."""
        from tools.contact_discovery import ContactDiscoveryTool
        from schemas.scraper_schemas import WebsiteResearchResult

        mock_result = WebsiteResearchResult(
            emails=["dupe@brand.com"],
            phones=[],
            whatsapp_numbers=[],
            postal_addresses=[],
            social_links={},
            contact_page_url=None,
            visited_urls=["https://testbrand.com"]
        )
        # Pre-populate lead with the same email
        lead = self._make_lead()
        lead.contacts.emails = ["dupe@brand.com"]

        with patch("tools.contact_discovery.WebsiteResearchService") as MockCrawler, \
             patch("tools.contact_discovery.DuckDuckGoSearchService") as MockSearch:
            MockCrawler.return_value.research_website.return_value = mock_result
            MockSearch.return_value.search.return_value = []
            tool = ContactDiscoveryTool(max_queries=2, max_pages=1, max_runtime_s=30)
            updated_lead, _ = tool.execute(lead)

        assert updated_lead.contacts.emails.count("dupe@brand.com") == 1
