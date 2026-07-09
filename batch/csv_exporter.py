import csv
import os
from typing import List
from loguru import logger
from models.domain import Lead


class CSVExporter:
    """Utility to export lead research result datasets to CSV files."""

    @staticmethod
    def export_leads(leads: List[Lead], filepath: str = "data/results.csv") -> None:
        """
        Exports a list of Lead objects to the specified CSV filepath.
        Includes all contact details, socials, maps links, confidence, tool runtime, and status.
        """
        try:
            dir_name = os.path.dirname(filepath)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
            headers = [
                "Brand", "Website", "Emails", "Phones", "Addresses",
                "Instagram", "Facebook", "LinkedIn", "Google Maps",
                "Confidence", "Runtime", "Status"
            ]
            
            with open(filepath, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                
                for lead in leads:
                    brand = lead.brand_name
                    website = lead.website or ""
                    emails = ", ".join(lead.contacts.emails)
                    phones = ", ".join(lead.contacts.phones)
                    addresses = "; ".join(lead.contacts.addresses)
                    instagram = lead.socials.instagram or ""
                    facebook = lead.socials.facebook or ""
                    linkedin = lead.socials.linkedin or ""
                    google_maps = lead.socials.google_maps or ""
                    confidence = f"{lead.confidence_score:.2f}"
                    
                    # Accumulate total runtime from tool duration profile maps
                    tool_durations = lead.enrichments.get("tool_durations", {})
                    runtime = sum(tool_durations.values()) if tool_durations else 0.0
                    
                    # Determine status
                    status = "completed"
                    if website == "unknown" or not website:
                        status = "failed"
                        
                    writer.writerow([
                        brand, website, emails, phones, addresses,
                        instagram, facebook, linkedin, google_maps,
                        confidence, f"{runtime:.2f}", status
                    ])
                    
            logger.info(f"Successfully exported {len(leads)} leads to: '{filepath}'")
            
        except Exception as e:
            logger.error(f"Failed to export leads to CSV file '{filepath}': {e}")
            raise e
