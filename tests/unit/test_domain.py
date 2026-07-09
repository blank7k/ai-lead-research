from models.domain import Brand, ContactInfo, Lead


def test_brand_creation(mock_brand):
    """Verify that a Brand model can be instantiated correctly with expected attributes."""
    assert mock_brand.name == "Nike"
    assert mock_brand.domain == "nike.com"
    assert mock_brand.category == "Footwear/D2C"
    assert mock_brand.id is None


def test_lead_creation(mock_brand, mock_contact_info):
    """Verify that a Lead model joins a Brand and ContactInfo correctly."""
    lead = Lead(
        brand=mock_brand,
        contact_info=mock_contact_info,
        is_verified=True,
        confidence_score=0.9
    )
    assert lead.brand.name == "Nike"
    assert "contact@nike.com" in lead.contact_info.emails
    assert lead.is_verified is True
    assert lead.confidence_score == 0.9
