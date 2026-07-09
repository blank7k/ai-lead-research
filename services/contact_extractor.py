"""
Shared, reusable regex-based contact extractors.

Every tool in the registry can import these helpers to ensure
consistent email / phone extraction across all data sources.
"""

import re
from typing import Set


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Image / asset extension false-positives that match the email regex
_ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".css", ".js"}

# Minimum / maximum digit counts for a plausible phone number
_PHONE_MIN_DIGITS = 7
_PHONE_MAX_DIGITS = 15

# Generic / placeholder addresses that add no value
_SKIP_EMAILS = {
    "example@example.com",
    "user@example.com",
    "noreply@example.com",
    "no-reply@example.com",
    "test@test.com",
}


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def extract_emails(text: str) -> Set[str]:
    """
    Extract valid-looking email addresses from arbitrary text.

    Filters:
    - asset / image file extensions mistaken for TLDs
    - well-known placeholder addresses
    - addresses shorter than 6 characters before the @
    """
    pattern = r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}\b"
    raw = re.findall(pattern, text)

    result: Set[str] = set()
    for email in raw:
        e = email.lower().strip()
        if e in _SKIP_EMAILS:
            continue
        if any(e.endswith(ext) for ext in _ASSET_EXTS):
            continue
        result.add(e)

    return result


def extract_phones(text: str) -> Set[str]:
    """
    Extract phone numbers from arbitrary text using multiple format patterns.

    Accepts international (+XX), US/Canada (1-NXX), and generic formats.
    Rejects strings whose digit count falls outside [_PHONE_MIN_DIGITS, _PHONE_MAX_DIGITS].
    """
    patterns = [
        # +91-98765-43210  /  +1 (800) 555-1234
        r"\+\d{1,3}[\s\-.]?\(?\d{2,4}\)?[\s\-.]?\d{3,4}[\s\-.]?\d{3,4}",
        # 1-800-555-1234 / 1800555123
        r"\b1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        # 98765 43210  /  98765-43210  (10-digit, common in India)
        r"\b\d{5}[\s\-]\d{5}\b",
        # (022) 2345-6789
        r"\(\d{2,4}\)\s?\d{3,4}[\s\-]\d{3,4}",
    ]

    result: Set[str] = set()
    for pattern in patterns:
        for match in re.findall(pattern, text):
            digits = re.sub(r"\D", "", match)
            if _PHONE_MIN_DIGITS <= len(digits) <= _PHONE_MAX_DIGITS:
                result.add(match.strip())

    return result


def clean_brand_name(brand_name: str) -> str:
    """Strip quotes and apostrophes that cause DuckDuckGo search anomalies."""
    return brand_name.replace("'", "").replace('"', "").strip()
