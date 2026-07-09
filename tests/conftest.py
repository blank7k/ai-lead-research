import pytest
from models.domain import Lead, Contacts, Socials


@pytest.fixture
def mock_contacts() -> Contacts:
    return Contacts(
        emails=["contact@nike.com"],
        phones=["1-800-806-6453"],
        addresses=["One Bowerman Dr, Beaverton, OR 97005"]
    )


@pytest.fixture
def mock_socials() -> Socials:
    return Socials(
        instagram="https://instagram.com/nike",
        linkedin="https://linkedin.com/company/nike",
        facebook="https://facebook.com/nike"
    )


@pytest.fixture
def mock_lead(mock_contacts, mock_socials) -> Lead:
    return Lead(
        brand_name="Nike",
        founder_name="Phil Knight",
        website="https://nike.com",
        category="Footwear/D2C",
        contacts=mock_contacts,
        socials=mock_socials,
        confidence_score=0.9,
        is_verified=True
    )
