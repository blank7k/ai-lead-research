from models.domain import Lead, Contacts, Socials


def test_lead_creation(mock_lead):
    """Verify that a Lead model is instantiated correctly with nested Contacts and Socials."""
    assert mock_lead.brand_name == "Nike"
    assert mock_lead.founder_name == "Phil Knight"
    assert mock_lead.website == "https://nike.com"
    assert "contact@nike.com" in mock_lead.contacts.emails
    assert mock_lead.socials.instagram == "https://instagram.com/nike"
    assert mock_lead.is_verified is True
    assert mock_lead.confidence_score == 0.9


def test_missing_fields_property():
    """Verify that the missing_fields property correctly identifies missing data gaps."""
    # 1. Start with completely empty lead
    lead = Lead(brand_name="Zara")
    missing = lead.missing_fields
    assert "website" in missing
    assert "emails" in missing
    assert "phones" in missing
    assert "founder" in missing

    # 2. Add website
    lead.website = "https://zara.com"
    missing = lead.missing_fields
    assert "website" not in missing
    assert "emails" in missing

    # 3. Add email
    lead.contacts.emails = ["info@zara.com"]
    missing = lead.missing_fields
    assert "emails" not in missing
    assert "phones" in missing

    # 4. Add phone
    lead.contacts.phones = ["+1-555-0100"]
    missing = lead.missing_fields
    assert "phones" not in missing
    assert "founder" in missing

    # 5. Add founder
    lead.founder_name = "Amancio Ortega"
    missing = lead.missing_fields
    assert len(missing) == 0
