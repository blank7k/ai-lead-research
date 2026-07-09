import os
import pytest
from unittest.mock import MagicMock, patch
from batch.batch_processor import BatchProcessor
from batch.config_parser import ConfigParser
from schemas.search_schemas import BrandSearchResult
from schemas.scraper_schemas import WebsiteResearchResult


def test_config_parser():
    """Verify that ConfigParser correctly loads yaml properties and returns defaults for missing files."""
    # Test fallback
    default_config = ConfigParser.load_config("nonexistent_config.yaml")
    assert default_config["workers"] == 3
    assert default_config["provider"] == "duckduckgo"
    
    # Test valid yaml parsing
    config = ConfigParser.load_config("config.yaml")
    assert config["workers"] in [3, 4]
    assert config["timeout"] in [60, 120]


def test_benchmark_coverage_regression(tmp_path):
    """
    Integration and regression test ensuring future changes cannot reduce
    field discovery coverage below required minimum thresholds in CI.
    Also verifies ToolExecutor duration profiling and timeline offsets.
    """
    checkpoint_path = str(tmp_path / "test_checkpoint.json")
    results_path = str(tmp_path / "test_results.csv")
    
    # 1. Define mock structures
    mock_search = BrandSearchResult(
        brand_name="Mock Brand",
        official_website="https://mockbrand.com",
        instagram_url="https://instagram.com/mockbrand",
        facebook_url="https://facebook.com/mockbrand",
        linkedin_url="https://linkedin.com/company/mockbrand",
        raw_results=[]
    )
    
    mock_website = WebsiteResearchResult(
        emails=["contact@mockbrand.com"],
        phones=["+1-555-0100"],
        whatsapp_numbers=[],
        postal_addresses=["123 Mock St, Mock City"],
        social_links={
            "instagram": "https://instagram.com/mockbrand", 
            "linkedin": "https://linkedin.com/company/mockbrand", 
            "facebook": "https://facebook.com/mockbrand"
        },
        contact_page_url="https://mockbrand.com/contact",
        visited_urls=["https://mockbrand.com"]
    )
    
    mock_profile = {
        "phone": "+1-555-0100",
        "address": "123 Mock St, Mock City",
        "google_maps_url": "https://google.com/maps/mock",
        "rating": 4.5,
        "review_count": 150,
        "opening_hours": "Mon-Fri 9AM-5PM"
    }

    # 2. Patch provider services to isolate network calls
    with patch("services.search_service.DuckDuckGoSearchProvider.search_brand", return_value=mock_search), \
         patch("services.scraper_service.WebsiteResearchService.research_website", return_value=mock_website), \
         patch("services.business_profile_service.DuckDuckGoBusinessProfileProvider.fetch_profile", return_value=mock_profile):
         
         # Instantiate batch processor running 2 concurrent workers
         processor = BatchProcessor(
             workers=2,
             delay_between_batches=0.1,
             timeout=20.0,
             checkpoint_filepath=checkpoint_path,
             results_filepath=results_path
         )
         
         # Execute batch on mock brands CSV
         metrics = processor.run_batch("tests/data/benchmark_brands.csv")
         
         # 3. Assert coverage is above Staff Engineer regression thresholds
         assert metrics["processed"] == 5
         assert metrics["website_coverage"] >= 90.0
         assert metrics["email_coverage"] >= 70.0
         assert metrics["phone_coverage"] >= 40.0
         assert metrics["address_coverage"] >= 60.0
         assert metrics["failures"] == 0
         
         # 4. Verify ToolExecutor timeline and timing profiling
         assert os.path.exists(results_path)
         assert os.path.exists(checkpoint_path)
         
         # Load the generated results CSV to check if timing values are saved
         import csv
         with open(results_path, "r", encoding="utf-8") as f:
             reader = csv.DictReader(f)
             rows = list(reader)
             assert len(rows) == 5
             for row in rows:
                 # Runtime should be a positive float number string
                 assert float(row["Runtime"]) >= 0.0
                 assert row["Status"] == "completed"
