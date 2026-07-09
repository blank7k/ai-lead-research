from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Type
from loguru import logger
from models.domain import Lead, Contacts, Socials
from services.search_service import DuckDuckGoSearchProvider
from services.scraper_service import WebsiteResearchService
from services.business_profile_service import DuckDuckGoBusinessProfileProvider


class IResearchTool(ABC):
    """Abstract interface defining the execution contract for all Research Agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Standardized unique identifier of the tool."""
        pass

    @abstractmethod
    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        """
        Execute the research tool on the current Lead context.
        
        Returns:
            Tuple[Lead, str]: The updated Lead model and a user-facing trace summary string.
        """
        pass


class SearchTool(IResearchTool):
    """Concrete tool executing DuckDuckGo search to locate brand endpoints."""

    @property
    def name(self) -> str:
        return "search_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        logger.info(f"[SearchTool] Querying brand name '{lead.brand_name}'")
        provider = DuckDuckGoSearchProvider()
        result = provider.search_brand(lead.brand_name)
        
        # Update Lead structure
        lead.website = result.official_website or "unknown"
        if result.instagram_url:
            lead.socials.instagram = result.instagram_url
        if result.facebook_url:
            lead.socials.facebook = result.facebook_url
        if result.linkedin_url:
            lead.socials.linkedin = result.linkedin_url
            
        # Compile trace
        status = "✓ Website Found" if result.official_website else "✗ Website Not Found"
        return lead, f"Search Tool\n{status}"


class WebsiteTool(IResearchTool):
    """Concrete tool executing deep crawler scans on the brand's domain."""

    @property
    def name(self) -> str:
        return "website_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        if not lead.website or lead.website == "unknown":
            logger.warning("[WebsiteTool] Scraper execution requested but website is unknown.")
            return lead, "Website Tool\n✗ Crawl Skipped: No Website"
            
        logger.info(f"[WebsiteTool] Crawling brand homepage '{lead.website}'")
        crawler = WebsiteResearchService()
        result = crawler.research_website(lead.website)
        
        # Merge Contacts
        lead.contacts.emails = sorted(list(set(lead.contacts.emails + result.emails)))
        lead.contacts.phones = sorted(list(set(lead.contacts.phones + result.phones)))
        lead.contacts.addresses = sorted(list(set(lead.contacts.addresses + result.postal_addresses)))
        
        # Merge Socials
        if result.social_links.get("instagram"):
            lead.socials.instagram = result.social_links["instagram"]
        if result.social_links.get("facebook"):
            lead.socials.facebook = result.social_links["facebook"]
        if result.social_links.get("linkedin"):
            lead.socials.linkedin = result.social_links["linkedin"]
        if result.social_links.get("twitter"):
            lead.socials.twitter = result.social_links["twitter"]
            
        # Update sources
        lead.sources = sorted(list(set(lead.sources + result.visited_urls)))
        
        # Compile trace details
        email_status = "✓ Emails Found" if result.emails else "✗ Emails Missing"
        phone_status = "✓ Phones Found" if result.phones else "✗ Phone Missing"
        
        return lead, f"Website Tool\n{email_status}\n{phone_status}"


class BusinessProfileTool(IResearchTool):
    """Concrete tool executing search-based extraction of business profiles / Maps listings."""

    @property
    def name(self) -> str:
        return "business_profile_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        logger.info(f"[BusinessProfileTool] Querying business profile for brand '{lead.brand_name}'")
        provider = DuckDuckGoBusinessProfileProvider()
        result = provider.fetch_profile(lead.brand_name)
        
        updated_any = False
        
        # 1. Merge phone number
        phone_val = result.get("phone")
        if phone_val and phone_val not in lead.contacts.phones:
            lead.contacts.phones.append(phone_val)
            updated_any = True
            
        # 2. Merge address
        addr_val = result.get("address")
        if addr_val and addr_val not in lead.contacts.addresses:
            lead.contacts.addresses.append(addr_val)
            updated_any = True
            
        # 3. Merge Google Maps url
        maps_url = result.get("google_maps_url")
        if maps_url and not lead.socials.google_maps:
            lead.socials.google_maps = maps_url
            updated_any = True
            
        # 4. Merge enrichments
        for key in ["rating", "review_count", "opening_hours"]:
            val = result.get(key)
            if val is not None and lead.enrichments.get(key) != val:
                lead.enrichments[key] = val
                updated_any = True
                
        # Only increase confidence score when new info was found
        if updated_any:
            # cap at 1.0
            lead.confidence_score = min(1.0, lead.confidence_score + 0.15)
            
        # Compile trace details
        phone_status = "✓ Phone Found" if phone_val else "✗ Phone Missing"
        addr_status = "✓ Address Found" if addr_val else "✗ Address Missing"
        maps_status = "✓ Maps Link Found" if maps_url else "✗ Maps Link Missing"
        
        return lead, f"Business Profile Tool\n{phone_status}\n{addr_status}\n{maps_status}"


class InstagramTool(IResearchTool):
    """Stub tool representing deep Instagram bio/post harvesting."""

    @property
    def name(self) -> str:
        return "instagram_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        logger.info("[InstagramTool] Stub executed.")
        return lead, "Instagram Tool\n(Not Implemented)"


class FacebookTool(IResearchTool):
    """Stub tool representing Facebook Page info harvesting."""

    @property
    def name(self) -> str:
        return "facebook_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        logger.info("[FacebookTool] Stub executed.")
        return lead, "Facebook Tool\n(Not Implemented)"


class LinkedInTool(IResearchTool):
    """Stub tool representing LinkedIn founder/company harvesting."""

    @property
    def name(self) -> str:
        return "linkedin_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        logger.info("[LinkedInTool] Stub executed.")
        return lead, "LinkedIn Tool\n(Not Implemented)"


class ToolRegistry:
    """Registry managing the life-cycle and lookup of AI agent research tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, IResearchTool] = {}
        # Pre-register built-in tools
        self.register(SearchTool())
        self.register(WebsiteTool())
        self.register(BusinessProfileTool())
        self.register(InstagramTool())
        self.register(FacebookTool())
        self.register(LinkedInTool())

    def register(self, tool: IResearchTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered research tool: '{tool.name}'")

    def get_tool(self, name: str) -> IResearchTool:
        """Retrieve a registered tool by its name key."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered in ToolRegistry.")
        return self._tools[name]

    def list_tools(self) -> List[str]:
        """List all registered tool identifiers."""
        return list(self._tools.keys())


# Singleton global instance
tool_registry = ToolRegistry()
