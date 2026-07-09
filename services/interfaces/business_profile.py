from abc import ABC, abstractmethod


class IBusinessProfileProvider(ABC):
    """Interface contract representing external business profile search providers."""

    @abstractmethod
    def fetch_profile(self, brand_name: str) -> dict:
        """
        Locate and parse public business listing/maps details for a given brand name.

        Args:
            brand_name: Name of the brand to research.

        Returns:
            dict: Discovered attributes with keys:
                - phone (str or None)
                - address (str or None)
                - website (str or None)
                - google_maps_url (str or None)
                - rating (float or None)
                - review_count (int or None)
                - opening_hours (str or None)
        """
        pass
