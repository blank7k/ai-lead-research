"""
ContactDiscoveryTool
====================
A standalone IResearchTool that runs a prioritised, budget-controlled
contact-discovery cascade.

Cascade order (stops early once both email AND phone are resolved):
  1. Official website deep-crawl  (reuses WebsiteResearchService)
  2. Contact-page search + crawl  (DuckDuckGo query → Playwright)
  3. Business / Maps snippets     (DuckDuckGo query)
  4. Facebook page snippets       (DuckDuckGo query)
  5. Instagram bio snippets       (DuckDuckGo query)
  6. LinkedIn company snippets    (DuckDuckGo query)

Each step:
  - generates an intelligent query based on brand name, website, and
    what is still missing
  - records *source* for every email / phone it discovers
  - respects a configurable budget: max_queries, max_pages, max_runtime_s

Output fields written to Lead:
  contacts.emails
  contacts.phones
  enrichments["email_sources"]   → {email: [source_url, ...]}
  enrichments["phone_sources"]   → {phone: [source_url, ...]}
"""

import time
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger
from playwright.sync_api import sync_playwright

from models.domain import Lead
from services.contact_extractor import extract_emails, extract_phones, clean_brand_name
from services.search_service import DuckDuckGoSearchService
from services.scraper_service import WebsiteResearchService
from tools.base import IResearchTool
from config.settings import settings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _Budget:
    """Tracks remaining search budget for a single ContactDiscoveryTool run."""

    def __init__(self, max_queries: int, max_pages: int, max_runtime_s: float) -> None:
        self.max_queries = max_queries
        self.max_pages = max_pages
        self.max_runtime_s = max_runtime_s
        self._queries_used = 0
        self._pages_used = 0
        self._start = time.time()

    def query_ok(self) -> bool:
        return (
            self._queries_used < self.max_queries
            and (time.time() - self._start) < self.max_runtime_s
        )

    def page_ok(self) -> bool:
        return (
            self._pages_used < self.max_pages
            and (time.time() - self._start) < self.max_runtime_s
        )

    def charge_query(self) -> None:
        self._queries_used += 1

    def charge_page(self) -> None:
        self._pages_used += 1

    def elapsed(self) -> float:
        return time.time() - self._start


class _Accumulator:
    """
    Accumulates emails / phones with their discovery sources.
    Deduplicates automatically.
    """

    def __init__(self) -> None:
        self.emails: Set[str] = set()
        self.phones: Set[str] = set()
        self.email_sources: Dict[str, List[str]] = {}
        self.phone_sources: Dict[str, List[str]] = {}

    def add_emails(self, found: Set[str], source: str) -> int:
        """Returns number of *new* emails added."""
        new = 0
        for e in found:
            if e not in self.emails:
                self.emails.add(e)
                new += 1
            self.email_sources.setdefault(e, [])
            if source not in self.email_sources[e]:
                self.email_sources[e].append(source)
        return new

    def add_phones(self, found: Set[str], source: str) -> int:
        """Returns number of *new* phones added."""
        new = 0
        for p in found:
            if p not in self.phones:
                self.phones.add(p)
                new += 1
            self.phone_sources.setdefault(p, [])
            if source not in self.phone_sources[p]:
                self.phone_sources[p].append(source)
        return new

    def has_email(self) -> bool:
        return bool(self.emails)

    def has_phone(self) -> bool:
        return bool(self.phones)

    def satisfied(self) -> bool:
        """True once at least one email AND one phone have been found."""
        return self.has_email() and self.has_phone()


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

class ContactDiscoveryTool(IResearchTool):
    """
    Intelligent contact-discovery cascade tool.

    Configurable via constructor so the research agent / tests can
    override budget parameters without touching the registry.
    """

    def __init__(
        self,
        max_queries: int = 8,
        max_pages: int = 3,
        max_runtime_s: float = 90.0,
    ) -> None:
        self._max_queries = max_queries
        self._max_pages = max_pages
        self._max_runtime_s = max_runtime_s

    # ------------------------------------------------------------------
    # IResearchTool interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "contact_discovery_tool"

    def execute(self, lead: Lead) -> Tuple[Lead, str]:
        logger.info(
            f"[ContactDiscoveryTool] Starting contact discovery cascade for '{lead.brand_name}'"
        )

        acc = _Accumulator()
        budget = _Budget(self._max_queries, self._max_pages, self._max_runtime_s)
        search_svc = DuckDuckGoSearchService()
        brand = lead.brand_name
        clean = clean_brand_name(brand)
        website = lead.website if lead.website and lead.website != "unknown" else None

        # Seed accumulator with contacts already on the lead (from earlier tools)
        for e in lead.contacts.emails:
            acc.add_emails({e}, "website_tool")
        for p in lead.contacts.phones:
            acc.add_phones({p}, "website_tool")

        # ── Step 1: Website deep-crawl ──────────────────────────────────
        if website and not acc.satisfied() and budget.page_ok():
            self._crawl_website(website, acc, budget)

        # ── Step 2: Contact-page search + crawl ────────────────────────
        if not acc.satisfied() and budget.query_ok():
            self._search_and_crawl_contact_page(clean, website, acc, budget, search_svc)

        # ── Steps 3-6: Snippet-based searches for each public source ───
        sources_to_try: List[Tuple[str, Optional[str]]] = [
            ("business",  None),
            ("facebook",  lead.socials.facebook),
            ("instagram", lead.socials.instagram),
            ("linkedin",  lead.socials.linkedin),
        ]

        for source_key, known_url in sources_to_try:
            if acc.satisfied():
                break
            if not budget.query_ok():
                break
            self._search_snippets(clean, website, source_key, known_url, acc, budget, search_svc)

        # ── Merge into lead ─────────────────────────────────────────────
        lead = self._merge(lead, acc)

        # ── Build trace summary ─────────────────────────────────────────
        trace = self._build_trace(acc, budget)
        logger.info(f"[ContactDiscoveryTool] Finished for '{brand}' in {budget.elapsed():.1f}s — {trace}")
        return lead, trace

    # ------------------------------------------------------------------
    # Step 1 – Deep-crawl the official website
    # ------------------------------------------------------------------

    def _crawl_website(self, website: str, acc: _Accumulator, budget: _Budget) -> None:
        """Reuse WebsiteResearchService to deep-crawl the official site."""
        logger.info(f"[ContactDiscoveryTool] Step 1 – crawling website: {website}")
        try:
            budget.charge_page()
            crawler = WebsiteResearchService()
            result = crawler.research_website(website)
            acc.add_emails(set(result.emails), website)
            acc.add_phones(set(result.phones), website)
            logger.debug(
                f"[ContactDiscoveryTool] Website crawl found "
                f"{len(result.emails)} emails, {len(result.phones)} phones."
            )
        except Exception as e:
            logger.error(f"[ContactDiscoveryTool] Website crawl failed: {e}")

    # ------------------------------------------------------------------
    # Step 2 – Search for a dedicated contact page, then crawl it
    # ------------------------------------------------------------------

    def _search_and_crawl_contact_page(
        self,
        clean_brand: str,
        website: Optional[str],
        acc: _Accumulator,
        budget: _Budget,
        search_svc: DuckDuckGoSearchService,
    ) -> None:
        """Find the brand's contact page via search and crawl it directly."""
        queries = self._contact_page_queries(clean_brand, website)
        contact_url: Optional[str] = None

        for q in queries:
            if not budget.query_ok():
                break
            try:
                budget.charge_query()
                hits = search_svc.search(q, max_results=5)
                # First hit whose URL contains the brand domain or "contact"
                for hit in hits:
                    url = hit.get("href", "")
                    # Also extract from snippet immediately
                    snippet = hit.get("body", "")
                    acc.add_emails(extract_emails(snippet), url or q)
                    acc.add_phones(extract_phones(snippet), url or q)

                    if contact_url:
                        continue
                    url_lower = url.lower()
                    if website and website.replace("https://", "").replace("http://", "") in url_lower:
                        if any(kw in url_lower for kw in ["contact", "support", "help", "reach"]):
                            contact_url = url
                    elif "contact" in url_lower and not any(
                        excl in url_lower for excl in ["instagram", "facebook", "linkedin", "twitter"]
                    ):
                        contact_url = url
            except Exception as e:
                logger.warning(f"[ContactDiscoveryTool] Contact page search failed ({q}): {e}")

            if acc.satisfied():
                return

        # Crawl the discovered contact page
        if contact_url and budget.page_ok():
            logger.info(f"[ContactDiscoveryTool] Step 2 – crawling contact page: {contact_url}")
            try:
                budget.charge_page()
                scraped = self._playwright_scrape(contact_url)
                acc.add_emails(extract_emails(scraped), contact_url)
                acc.add_phones(extract_phones(scraped), contact_url)
            except Exception as e:
                logger.warning(f"[ContactDiscoveryTool] Contact page crawl failed: {e}")

    # ------------------------------------------------------------------
    # Steps 3-6 – DuckDuckGo snippet-mining per source
    # ------------------------------------------------------------------

    def _search_snippets(
        self,
        clean_brand: str,
        website: Optional[str],
        source_key: str,
        known_url: Optional[str],
        acc: _Accumulator,
        budget: _Budget,
        search_svc: DuckDuckGoSearchService,
    ) -> None:
        """Run targeted DuckDuckGo queries and mine contact data from result snippets."""
        queries = self._source_queries(clean_brand, website, source_key, known_url)
        logger.info(
            f"[ContactDiscoveryTool] Step '{source_key}' – running {len(queries)} queries"
        )

        for q in queries:
            if not budget.query_ok() or acc.satisfied():
                break
            try:
                budget.charge_query()
                hits = search_svc.search(q, max_results=5)
                for hit in hits:
                    text = hit.get("body", "") + " " + hit.get("title", "")
                    source_url = hit.get("href", source_key)
                    acc.add_emails(extract_emails(text), source_url)
                    acc.add_phones(extract_phones(text), source_url)
            except Exception as e:
                logger.warning(f"[ContactDiscoveryTool] Snippet search failed ({q}): {e}")

    # ------------------------------------------------------------------
    # Query generators
    # ------------------------------------------------------------------

    def _contact_page_queries(self, clean_brand: str, website: Optional[str]) -> List[str]:
        """Generate intelligent queries to locate a brand's contact page."""
        queries = [
            f'"{clean_brand}" contact us email phone',
            f"{clean_brand} contact page email",
        ]
        if website:
            domain = website.replace("https://", "").replace("http://", "").split("/")[0]
            queries.insert(0, f"site:{domain} contact")
        return queries

    def _source_queries(
        self,
        clean_brand: str,
        website: Optional[str],
        source_key: str,
        known_url: Optional[str],
    ) -> List[str]:
        """
        Generate intelligent queries per public source.
        Integrates the known social/profile URL when available.
        """
        base: Dict[str, List[str]] = {
            "business": [
                f'"{clean_brand}" business contact phone address',
                f'"{clean_brand}" customer service phone number',
                f"{clean_brand} india contact number",
            ],
            "facebook": [
                f'"{clean_brand}" facebook contact email phone',
                f"site:facebook.com {clean_brand} contact",
            ],
            "instagram": [
                f'"{clean_brand}" instagram contact email',
                f"site:instagram.com {clean_brand}",
            ],
            "linkedin": [
                f'"{clean_brand}" linkedin company email',
                f"site:linkedin.com/company {clean_brand} contact",
            ],
        }

        queries = base.get(source_key, [])

        # Prepend a query using the known URL if available
        if known_url:
            queries.insert(0, f'"{clean_brand}" {known_url} email phone contact')

        return queries

    # ------------------------------------------------------------------
    # Playwright one-shot scrape (no full browser session)
    # ------------------------------------------------------------------

    def _playwright_scrape(self, url: str) -> str:
        """Scrape visible body text from a single URL using Playwright."""
        text = ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=settings.BROWSER_HEADLESS)
                ctx = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = ctx.new_page()
                page.goto(url, timeout=settings.BROWSER_TIMEOUT_MS, wait_until="load")
                text = page.locator("body").inner_text() or ""
                browser.close()
        except Exception as e:
            logger.warning(f"[ContactDiscoveryTool] Playwright scrape failed for {url}: {e}")
        return text

    # ------------------------------------------------------------------
    # Merge results into Lead
    # ------------------------------------------------------------------

    def _merge(self, lead: Lead, acc: _Accumulator) -> Lead:
        """Write discovered contacts + source maps back onto the lead."""
        # Merge emails (deduplicate preserving order)
        existing = set(lead.contacts.emails)
        for e in sorted(acc.emails):
            if e not in existing:
                lead.contacts.emails.append(e)
                existing.add(e)

        # Merge phones (deduplicate preserving order)
        existing_p = set(lead.contacts.phones)
        for p in sorted(acc.phones):
            if p not in existing_p:
                lead.contacts.phones.append(p)
                existing_p.add(p)

        # Persist source maps
        lead.enrichments["email_sources"] = acc.email_sources
        lead.enrichments["phone_sources"] = acc.phone_sources

        # Bump confidence proportionally to what was found
        gained = (1 if acc.has_email() else 0) + (1 if acc.has_phone() else 0)
        lead.confidence_score = min(1.0, lead.confidence_score + gained * 0.1)

        return lead

    # ------------------------------------------------------------------
    # Trace builder
    # ------------------------------------------------------------------

    def _build_trace(self, acc: _Accumulator, budget: _Budget) -> str:
        email_str = ", ".join(sorted(acc.emails)) if acc.emails else "none"
        phone_str = ", ".join(sorted(acc.phones)) if acc.phones else "none"
        return (
            f"Contact Discovery Tool\n"
            f"{'✓' if acc.has_email() else '✗'} Emails: {email_str}\n"
            f"{'✓' if acc.has_phone() else '✗'} Phones: {phone_str}\n"
            f"Queries used: {budget._queries_used}/{budget.max_queries} | "
            f"Runtime: {budget.elapsed():.1f}s"
        )
