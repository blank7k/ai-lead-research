from typing import Optional
from loguru import logger
from models.domain import Lead


class DecisionEngine:
    """Rules engine to dynamically choose the next research tool based on missing lead details."""

    @staticmethod
    def get_next_tool(lead: Lead) -> Optional[str]:
        """
        Evaluate the Lead data status and select the next tool to invoke.
        Ensures no tool is executed more than once per lead to prevent infinite loops.

        Priority order:
          1. search_tool            – discover the website
          2. website_tool           – deep-crawl the website for contacts
          3. business_profile_tool  – phone / address / Maps via search snippets
          4. contact_discovery_tool – intelligent cascade (contact page, FB, IG, LI snippets)
          5. linkedin_tool          – founder lookup (stub)

        Args:
            lead: The current Lead data state.

        Returns:
            Optional[str]: Key of the next tool to run, or None if research is complete.
        """
        missing = lead.missing_fields
        trace = lead.execution_trace

        logger.debug(f"[DecisionEngine] Evaluating gaps. Missing: {missing}, Executed: {trace}")

        # Rule 1: Website is missing
        if "website" in missing:
            if "search_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Website missing -> search_tool")
                return "search_tool"

        # Rule 2: Website exists but emails or phones are missing – crawl it first
        if "website" not in missing and ("emails" in missing or "phones" in missing):
            if "website_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Website exists but contact info incomplete -> website_tool")
                return "website_tool"

        # Rule 3: Phone, address, or Maps URL is missing
        if "phones" in missing or "addresses" in missing or "google_maps" in missing:
            if "business_profile_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Phone, Address, or Maps missing -> business_profile_tool")
                return "business_profile_tool"

        # Rule 4: Email or phone STILL missing after website + business profile
        #         → run the intelligent contact-discovery cascade
        if "emails" in missing or "phones" in missing:
            if "contact_discovery_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Email/phone still missing -> contact_discovery_tool")
                return "contact_discovery_tool"

        # Rule 5: Founder details missing
        if "founder" in missing:
            if "linkedin_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Founder missing -> linkedin_tool")
                return "linkedin_tool"

        # All gaps resolved or tools exhausted
        logger.info("[DecisionEngine] Gaps resolved or tool options exhausted. Research complete.")
        return None
