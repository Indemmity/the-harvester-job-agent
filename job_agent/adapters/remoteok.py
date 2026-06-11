from __future__ import annotations

import html as html_module
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import requests

from ..exceptions import SourceAdapterError
from ..models import SearchFilters
from ..utils import clean_text, repair_mojibake
from .base import SourceAdapter

LOGGER = logging.getLogger(__name__)

REMOTEOK_API_URL = "https://remoteok.com/api"
REMOTEOK_TIMEOUT_SECONDS = 30
REMOTEOK_USER_AGENT = "job-agent/0.1.0 (+https://remoteok.com)"

ROLE_SYNONYMS: dict[str, set[str]] = {
    "developer": {"engineer", "dev", "programmer"},
    "engineer": {"developer", "dev", "programmer"},
    "dev": {"developer", "engineer", "programmer"},
    "frontend": {"front-end", "front end"},
    "backend": {"back-end", "back end"},
    "fullstack": {"full stack", "full-stack"},
    "qa": {"quality assurance", "tester", "test"},
    "product": {"pm"},
    "pm": {"product"},
}

GENERIC_QUERY_TOKENS = {
    "senior",
    "sr",
    "jr",
    "junior",
    "lead",
    "principal",
    "staff",
    "mid",
    "midlevel",
    "mid-level",
    "entry",
    "entrylevel",
    "entry-level",
    "remote",
    "remoteonly",
    "remote-only",
}

PHRASE_NORMALIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bfront[\s-]?end\b", re.IGNORECASE), "frontend"),
    (re.compile(r"\bback[\s-]?end\b", re.IGNORECASE), "backend"),
    (re.compile(r"\bfull[\s-]?stack\b", re.IGNORECASE), "fullstack"),
    (re.compile(r"\bquality assurance\b", re.IGNORECASE), "qa"),
)

JOB_TYPE_TAGS = {
    "full time",
    "part time",
    "contract",
    "freelance",
    "internship",
    "temporary",
    "seasonal",
    "permanent",
}


class RemoteOKAdapter(SourceAdapter):
    source_name = "remoteok"
    implemented = True

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_seconds: int = REMOTEOK_TIMEOUT_SECONDS,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        user_agent = clean_text(self.session.headers.get("User-Agent"))
        if not user_agent or user_agent.startswith("python-requests/"):
            self.session.headers["User-Agent"] = REMOTEOK_USER_AGENT
        self.session.headers.setdefault("Accept", "application/json, text/plain, */*")

    def collect(self, title: str, filters: SearchFilters) -> list[Mapping[str, Any]]:
        query = clean_text(title)
        if not query:
            return []

        jobs = self._fetch_jobs()
        matched_jobs: list[Mapping[str, Any]] = []
        for record in jobs:
            if not self._is_job_record(record):
                continue
            if not self._matches_query(record, query, filters):
                continue
            matched_jobs.append(self._map_record(record, query))

        LOGGER.info(
            "RemoteOK matched %s of %s jobs for title=%s",
            len(matched_jobs),
            len(jobs),
            query,
        )
        return matched_jobs

    def _fetch_jobs(self) -> list[Mapping[str, Any]]:
        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(REMOTEOK_API_URL, timeout=self.timeout_seconds)
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException as exc:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    LOGGER.warning(
                        "RemoteOK API fetch failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1, max_retries, delay, exc
                    )
                    time.sleep(delay)
                else:
                    raise SourceAdapterError(f"Failed to fetch the RemoteOK API feed after {max_retries} retries: {exc}") from exc
            except ValueError as exc:
                raise SourceAdapterError("RemoteOK returned invalid JSON.") from exc

        if not isinstance(payload, list):
            raise SourceAdapterError("RemoteOK API returned an unexpected payload shape.")

        jobs = [item for item in payload if isinstance(item, Mapping)]
        LOGGER.debug("RemoteOK API payload contained %s mapped records", len(jobs))
        return jobs

    def _is_job_record(self, record: Mapping[str, Any]) -> bool:
        return bool(clean_text(record.get("position"))) and bool(clean_text(record.get("company")))

    def _matches_query(
        self,
        record: Mapping[str, Any],
        query: str,
        filters: SearchFilters,
    ) -> bool:
        position = self._display_text(record.get("position"))
        location = self._display_text(record.get("location"))
        description = self._strip_html(record.get("description"))
        tags = self._normalize_tags(record.get("tags"))
        
        candidate_blob = self._normalize_text(
            " ".join(
                value
                for value in [position, location, description, " ".join(tags)]
                if value
            )
        )
        
        # More flexible title matching - check if at least 50% of query words appear in title
        if not query:
            return True
        
        query_words = [word.casefold() for word in query.split()]
        position_lower = position.casefold()
        
        # Count how many query words match
        matched_words = sum(1 for word in query_words if word in position_lower)
        if matched_words == 0:
            return False
        # If we have multiple words, require at least 50% to match
        if len(query_words) > 1 and matched_words < len(query_words) * 0.5:
            return False

        if filters.location:
            normalized_location = self._normalize_text(filters.location)
            normalized_job_location = self._normalize_text(location)
            
            # Handle common location variations
            location_variations = {
                "bangalore": ["bengaluru", "bengaluru urban", "bangalore urban"],
                "bengaluru": ["bangalore", "bengaluru urban", "bangalore urban"],
                "india": [],  # India matches all locations in India
            }
            
            # Check if location matches directly or through variations
            location_matches = False
            if normalized_location in normalized_job_location:
                location_matches = True
            elif normalized_location in location_variations:
                variations = location_variations[normalized_location]
                if variations:
                    location_matches = any(var in normalized_job_location for var in variations)
                else:
                    # If no variations (like "India"), match any location
                    location_matches = True
            
            if not location_matches:
                return False

        if filters.experience_level:
            normalized_experience = self._normalize_text(filters.experience_level)
            if normalized_experience not in candidate_blob:
                return False

        if filters.date_posted:
            if not self._matches_date_filter(record, filters.date_posted):
                return False

        # RemoteOK is a remote-only board, so remote_only is satisfied by definition.
        return True

    def _map_record(self, record: Mapping[str, Any], query: str) -> dict[str, str]:
        posted_date = self._normalize_posted_date(record)
        salary = self._format_salary(record)
        description_snippet = self._build_description_snippet(record.get("description"))
        job_type = self._extract_job_type(record.get("tags"))

        return {
            "source": self.source_name,
            "title": self._display_text(record.get("position")),
            "company": self._display_text(record.get("company")),
            "location": self._display_text(record.get("location")),
            "job_type": job_type,
            "salary": salary,
            "job_url": clean_text(record.get("url") or record.get("apply_url")),
            "posted_date": posted_date,
            "scraped_at": "",
            "description_snippet": description_snippet,
            "search_keyword": query,
        }

    def _matches_date_filter(self, record: Mapping[str, Any], date_posted: str) -> bool:
        normalized_filter = clean_text(date_posted).casefold()
        posted_at = self._parse_posted_datetime(record)
        if posted_at is None:
            return False

        relative_match = re.fullmatch(
            r"(?P<amount>\d+)\s*(?P<unit>d|day|days|h|hour|hours|w|week|weeks)",
            normalized_filter,
        )
        if relative_match:
            amount = int(relative_match.group("amount"))
            unit = relative_match.group("unit")
            now = datetime.now(timezone.utc)
            if unit.startswith("h"):
                cutoff = now - timedelta(hours=amount)
            elif unit.startswith("w"):
                cutoff = now - timedelta(weeks=amount)
            else:
                cutoff = now - timedelta(days=amount)
            return posted_at >= cutoff

        if normalized_filter in posted_at.date().isoformat().casefold():
            return True

        posted_text = self._normalize_posted_date(record).casefold()
        return normalized_filter in posted_text

    def _parse_posted_datetime(self, record: Mapping[str, Any]) -> datetime | None:
        date_value = clean_text(record.get("date"))
        if date_value:
            try:
                parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except ValueError:
                parsed = None
            else:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed

        epoch_value = record.get("epoch")
        try:
            epoch_int = int(epoch_value)
        except (TypeError, ValueError):
            return None

        return datetime.fromtimestamp(epoch_int, tz=timezone.utc)

    def _normalize_posted_date(self, record: Mapping[str, Any]) -> str:
        date_value = clean_text(record.get("date"))
        if date_value:
            try:
                parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except ValueError:
                return date_value
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.replace(microsecond=0).isoformat()

        posted_at = self._parse_posted_datetime(record)
        if posted_at is None:
            return ""
        return posted_at.replace(microsecond=0).isoformat()

    def _format_salary(self, record: Mapping[str, Any]) -> str:
        salary_min = self._safe_int(record.get("salary_min"))
        salary_max = self._safe_int(record.get("salary_max"))

        if salary_min <= 0 and salary_max <= 0:
            return ""
        if salary_min > 0 and salary_max > 0 and salary_min != salary_max:
            return f"${salary_min:,} - ${salary_max:,}"
        salary_value = salary_max if salary_max > 0 else salary_min
        return f"${salary_value:,}"

    def _extract_job_type(self, tags_value: object) -> str:
        tags = self._normalize_tags(tags_value)
        for tag in tags:
            if tag in JOB_TYPE_TAGS:
                return tag
        return ""

    def _build_description_snippet(self, description: object) -> str:
        text = self._strip_html(description)
        if len(text) <= 240:
            return text
        return text[:240].rstrip() + "..."

    def _strip_html(self, value: object) -> str:
        text = repair_mojibake(value)
        if not text:
            return ""
        text = html_module.unescape(text)
        text = re.sub(r"<[^>]+>", " ", text)
        return clean_text(text)

    def _normalize_tags(self, tags_value: object) -> list[str]:
        if not isinstance(tags_value, list):
            return []
        normalized_tags = []
        for tag in tags_value:
            cleaned = repair_mojibake(tag).casefold()
            if cleaned:
                normalized_tags.append(cleaned)
        return normalized_tags

    def _normalize_text(self, text: str) -> str:
        normalized = repair_mojibake(text).casefold()
        for pattern, replacement in PHRASE_NORMALIZATIONS:
            normalized = pattern.sub(replacement, normalized)
        normalized = normalized.replace("e-commerce", "ecommerce")
        normalized = normalized.replace("full stack", "fullstack")
        normalized = normalized.replace("front end", "frontend")
        normalized = normalized.replace("back end", "backend")
        normalized = normalized.replace("machine learning", "machinelearning")
        return normalized

    def _display_text(self, value: object) -> str:
        return repair_mojibake(value)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", self._normalize_text(text))

    def _query_tokens(self, query: str) -> list[str]:
        tokens = self._tokenize(query)
        return [token for token in tokens if token not in GENERIC_QUERY_TOKENS]

    def _token_matches(self, token: str, candidate_tokens: set[str]) -> bool:
        if token in candidate_tokens:
            return True
        synonyms = ROLE_SYNONYMS.get(token, set())
        if any(synonym in candidate_tokens for synonym in synonyms):
            return True
        if token == "machinelearning":
            return "machine" in candidate_tokens and "learning" in candidate_tokens
        return False

    def _safe_int(self, value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
