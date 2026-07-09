import pytest
from models.domain import Brand, ContactInfo, Lead


@pytest.fixture
def mock_brand() -> Brand:
    return Brand(
        name="Nike",
        website_url="https://nike.com",
        domain="nike.com",
        category="Footwear/D2C"
    )


@pytest.fixture
def mock_contact_info() -> ContactInfo:
    return ContactInfo(
        emails=["contact@nike.com"],
        phones=["1-800-806-6453"],
        instagram_url="https://instagram.com/nike",
        linkedin_url="https://linkedin.com/company/nike",
        contact_page_url="https://nike.com/help"
    )
