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

        # Rule 2: Website exists but emails or phones are missing
        if "website" not in missing and ("emails" in missing or "phones" in missing):
            if "website_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Website exists but contact info incomplete -> website_tool")
                return "website_tool"

        # Rule 3: Phone is missing
        if "phones" in missing:
            if "google_business_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Phone missing -> google_business_tool")
                return "google_business_tool"

        # Rule 4: Email is still missing
        if "emails" in missing:
            if "instagram_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Email still missing -> instagram_tool")
                return "instagram_tool"

        # Rule 5: Founder details missing
        if "founder" in missing:
            if "linkedin_tool" not in trace:
                logger.info("[DecisionEngine] Rule match: Founder missing -> linkedin_tool")
                return "linkedin_tool"

        # If no missing fields require further tools, or all matched tools have already run
        logger.info("[DecisionEngine] Gaps resolved or tool options exhausted. Research complete.")
        return None
