import csv
import os
from typing import List
from loguru import logger


class CSVLoader:
    """Utility to load and validate target D2C brand names from a CSV file."""

    @staticmethod
    def load_brands(filepath: str) -> List[str]:
        """
        Reads brand names from the first column of the given CSV file.
        Skips empty lines, trims whitespace, and automatically skips header rows.
        """
        if not os.path.exists(filepath):
            logger.error(f"CSV file not found at path: '{filepath}'")
            raise FileNotFoundError(f"Target CSV file not found: {filepath}")
            
        brands = []
        try:
            # open with utf-8-sig to automatically strip byte order marks (BOM)
            with open(filepath, mode="r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                
                try:
                    first_row = next(reader)
                except StopIteration:
                    logger.warning(f"CSV file '{filepath}' is empty.")
                    return []
                    
                # Check if first row is a header row
                has_header = False
                if first_row and len(first_row) > 0:
                    first_val = first_row[0].strip().lower()
                    if first_val in ["brand_name", "brand", "name", "brands", "brandname"]:
                        has_header = True
                    else:
                        cleaned = first_row[0].strip()
                        if cleaned:
                            brands.append(cleaned)

                for row in reader:
                    if not row or len(row) == 0:
                        continue
                    val = row[0].strip()
                    if val and not val.startswith("#"):
                        brands.append(val)
                        
            # Deduplicate while preserving CSV order
            seen = set()
            unique_brands = []
            for b in brands:
                if b not in seen:
                    seen.add(b)
                    unique_brands.append(b)
                    
            logger.info(f"Successfully loaded {len(unique_brands)} unique brands from '{filepath}' (Header detected: {has_header})")
            return unique_brands
            
        except Exception as e:
            logger.error(f"Failed to parse CSV file '{filepath}': {e}")
            raise e
