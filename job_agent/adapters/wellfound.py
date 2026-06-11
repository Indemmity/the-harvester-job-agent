from __future__ import annotations

import logging
import os
import time
from typing import Any, Mapping

from firecrawl import FirecrawlApp

from ..exceptions import SourceAdapterError
from ..models import SearchFilters
from ..utils import clean_text
from .base import SourceAdapter

LOGGER = logging.getLogger(__name__)

WELLFOUND_BASE_URL = "https://www.wellfound.com"
WELLFOUND_SEARCH_URL_TEMPLATE = "{base_url}/role/{slug}"


class WellfoundAdapter(SourceAdapter):
    source_name = "wellfound"
    implemented = True

    def __init__(self, timeout: int = 30) -> None:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise SourceAdapterError(
                "FIRECRAWL_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )
        self.app = FirecrawlApp(api_key=api_key)
        self.timeout = timeout

    def collect(self, title: str, filters: SearchFilters) -> list[Mapping[str, Any]]:
        slug = title.lower().replace(" ", "-")
        
        # Use location-specific URL format if location is provided
        if filters.location:
            location_slug = filters.location.lower().replace(" ", "-")
            url = f"{WELLFOUND_BASE_URL}/role/l/{slug}/{location_slug}"
        else:
            url = WELLFOUND_SEARCH_URL_TEMPLATE.format(
                base_url=WELLFOUND_BASE_URL, slug=slug
            )

        LOGGER.info("Scraping Wellfound for title=%s location=%s url=%s", title, filters.location, url)

        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                scrape_result = self.app.scrape_url(url)
                break
            except Exception as exc:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    LOGGER.warning(
                        "Firecrawl scrape failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, max_retries, delay, exc
                    )
                    time.sleep(delay)
                else:
                    raise SourceAdapterError(f"Firecrawl scrape failed for {url} after {max_retries} retries: {exc}") from exc

        if not scrape_result or not scrape_result.get("markdown"):
            LOGGER.warning("No markdown content returned from Firecrawl for %s", url)
            return []

        markdown_content = scrape_result.get("markdown", "")
        LOGGER.debug("Wellfound markdown content: %s", markdown_content[:500])
        jobs = self._parse_wellfound_markdown(markdown_content, title, filters)

        LOGGER.info("Wellfound parsed %d jobs for title=%s", len(jobs), title)
        return jobs

    def _parse_wellfound_markdown(
        self, markdown: str, query: str, filters: SearchFilters
    ) -> list[Mapping[str, Any]]:
        jobs: list[Mapping[str, Any]] = []

        lines = markdown.split("\n")
        current_job: dict[str, Any] = {}
        in_job_section = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for company links in markdown format: [**Company Name**](url)
            if line.startswith("[**") and "**" in line and "](" in line:
                if current_job and current_job.get("company"):
                    if self._matches_query(current_job, query, filters):
                        jobs.append(current_job)
                    current_job = {}

                # Extract company name and URL
                start = line.find("[**") + 3
                end = line.find("**]")
                if start > 2 and end > start:
                    company = line[start:end].strip()
                    current_job["company"] = company

                    # Extract company URL
                    url_start = line.find("](") + 2
                    url_end = line.find(")")
                    if url_start > 1 and url_end > url_start:
                        company_url = line[url_start:url_end].strip()
                        current_job["company_url"] = company_url
                        # Construct job URL from company URL (Wellfound jobs are typically at company pages)
                        current_job["job_url"] = company_url

                    in_job_section = True
                    current_job["title"] = query  # Default to query title

            # Look for location information (appears after company, often with bullet points)
            elif in_job_section and not current_job.get("location"):
                # Location often appears as: "Remote • New York City" or "In office • San Francisco"
                if "•" in line or ("remote" in line.lower() or "office" in line.lower()):
                    # Clean up location text
                    location = line.replace("•", " ").strip()
                    # Remove common prefixes
                    location = location.replace("In office", "").replace("Remote only", "").replace("Remote", "").strip()
                    # Remove timezone offsets like "+1", "+4"
                    location = location.replace("+1", "").replace("+4", "").replace("+8", "").strip()
                    if location and len(location) < 100 and location not in ["any city", "Search"]:  # Reasonable location length
                        current_job["location"] = location

            # Look for job description or role details
            elif in_job_section and line and not line.startswith("[") and not line.startswith("!"):
                if not current_job.get("description"):
                    current_job["description"] = line

        # Add the last job if it exists
        if current_job and current_job.get("company") and self._matches_query(current_job, query, filters):
            jobs.append(current_job)

        return jobs

    def _matches_query(
        self, job: Mapping[str, Any], query: str, filters: SearchFilters
    ) -> bool:
        title = job.get("title", "")
        if not title:
            return False

        # More flexible title matching - check if at least 50% of query words appear in title
        query_words = [word.casefold() for word in query.split()]
        title_lower = title.casefold()
        
        # Count how many query words match
        matched_words = sum(1 for word in query_words if word in title_lower)
        if matched_words == 0:
            return False
        # If we have multiple words, require at least 50% to match
        if len(query_words) > 1 and matched_words < len(query_words) * 0.5:
            return False

        # Location filter - handle common variations
        if filters.location:
            location = job.get("location", "")
            if not location:
                return False
            
            filter_location = filters.location.casefold()
            location_lower = location.casefold()
            
            # Handle common location variations
            location_variations = {
                "bangalore": ["bengaluru", "bengaluru urban", "bangalore urban"],
                "bengaluru": ["bangalore", "bengaluru urban", "bangalore urban"],
                "india": [],  # India matches all locations in India
            }
            
            # Check if location matches directly or through variations
            location_matches = False
            if filter_location in location_lower:
                location_matches = True
            elif filter_location in location_variations:
                variations = location_variations[filter_location]
                if variations:
                    location_matches = any(var in location_lower for var in variations)
                else:
                    # If no variations (like "India"), match any location
                    location_matches = True
            
            if not location_matches:
                return False

        return True

