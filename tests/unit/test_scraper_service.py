from unittest.mock import MagicMock, patch
import pytest
from bs4 import BeautifulSoup
from services.scraper_service import WebsiteResearchService


def test_extract_emails():
    """Verify that email extraction parses valid emails and ignores static image assets."""
    service = WebsiteResearchService()
    email_set = set()
    text = "Send an email to contact@nike.com or hello@nike.co.uk. Ignore user@2x.png and logo@nike.svg"
    service._extract_emails(text, email_set)
    
    assert "contact@nike.com" in email_set
    assert "hello@nike.co.uk" in email_set
    assert "user@2x.png" not in email_set
    assert "logo@nike.svg" not in email_set


def test_extract_phones():
    """Verify phone numbers in different formats are correctly matched while random numbers are ignored."""
    service = WebsiteResearchService()
    phone_set = set()
    text = "Get in touch: +1 (555) 123-4567 or 1-800-800-8000. Item SKU: 8472910."
    service._extract_phones(text, phone_set)
    
    assert "+1 (555) 123-4567" in phone_set
    assert "1-800-800-8000" in phone_set
    assert "8472910" not in phone_set


def test_extract_addresses():
    """Verify address parsing from HTML5 address tags and regex/clue patterns."""
    service = WebsiteResearchService()
    address_set = set()
    html_markup = """
    <div>
        <address>  123 Fashion Lane, Beaverton, OR 97005  </address>
        <p>Our HQ is located at 456 Runway Road, Suite 300, California</p>
    </div>
    """
    soup = BeautifulSoup(html_markup, "html.parser")
    text = soup.get_text(separator=" ")
    service._extract_addresses(soup, text, address_set)
    
    assert "123 Fashion Lane, Beaverton, OR 97005" in address_set
    assert "Our HQ is located at 456 Runway Road, Suite 300, California" in address_set


def test_parse_hrefs():
    """Verify link categorization separates socials, WhatsApp redirects, and crawlable internal paths."""
    service = WebsiteResearchService()
    html_markup = """
    <div>
        <a href="https://instagram.com/brand">Instagram</a>
        <a href="https://facebook.com/brand/sharer">Share on Facebook</a>
        <a href="https://facebook.com/brand-official">Facebook Page</a>
        <a href="https://wa.me/15550199?text=Hello">WhatsApp Us</a>
        <a href="/about-us">About</a>
        <a href="https://partner-retailer.com/brand">Retailer Page</a>
    </div>
    """
    soup = BeautifulSoup(html_markup, "html.parser")
    whatsapp = set()
    socials = {}
    
    links = service._parse_hrefs(
        soup=soup,
        current_url="https://brand.com/home",
        target_domain="brand.com",
        whatsapp_set=whatsapp,
        socials_dict=socials
    )
    
    # Assert Socials
    assert socials["instagram"] == "https://instagram.com/brand"
    assert socials["facebook"] == "https://facebook.com/brand-official"
    # Verify sharer links are ignored
    assert "https://facebook.com/brand/sharer" not in socials.values()
    
    # Assert WhatsApp
    assert "15550199" in whatsapp
    
    # Assert Crawler Links
    assert "https://brand.com/about-us" in links
    assert "https://partner-retailer.com/brand" not in links


@patch("services.scraper_service.sync_playwright")
def test_crawler_loop(mock_sync_playwright):
    """Verify that the crawler cycles through internal links up to max_pages and builds the result schema."""
    # Arrange: Setup Playwright mocks
    mock_playwright = MagicMock()
    mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
    
    mock_browser = MagicMock()
    mock_playwright.chromium.launch.return_value = mock_browser
    
    mock_context = MagicMock()
    mock_browser.new_context.return_value = mock_context
    
    mock_page = MagicMock()
    mock_context.new_page.return_value = mock_page
    
    # Mock page content and link patterns
    mock_page.content.side_effect = [
        # Page 1: Home
        '<html><body><a href="/contact">Contact Us</a><p>Email: contact@brand.com</p></body></html>',
        # Page 2: Contact page
        '<html><body><p>Phone: +1 555 123-4567</p><address>100 Brand St, NY</address></body></html>'
    ]
    mock_page.locator.return_value.inner_text.side_effect = [
        "Email: contact@brand.com",
        "Phone: +1 555 123-4567 100 Brand St, NY"
    ]
    
    service = WebsiteResearchService()
    service.max_pages = 2 # limit pages to 2 for instant test execution
    
    # Act
    result = service.research_website("https://brand.com")
    
    # Assert
    assert "contact@brand.com" in result.emails
    assert "+1 555 123-4567" in result.phones
    assert "100 Brand St, NY" in result.postal_addresses
    assert "https://brand.com/contact" in result.visited_urls
    assert len(result.visited_urls) == 2
