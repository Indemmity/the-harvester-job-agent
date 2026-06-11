from __future__ import annotations

import logging
import re
import shutil
from typing import Any, Mapping
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..exceptions import SourceAdapterError
from ..models import SearchFilters
from ..utils import clean_text, repair_mojibake
from .base import SourceAdapter

LOGGER = logging.getLogger(__name__)

NAUKRI_HOME_URL = "https://www.naukri.com"
NAUKRI_SEARCH_URL_TEMPLATE = "https://www.naukri.com/{slug}-jobs"
NAUKRI_TIMEOUT_SECONDS = 30
NAUKRI_RENDER_TIMEOUT_SECONDS = 25
NAUKRI_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
NAUKRI_BLOCKED_MARKERS = (
    "Access Denied",
    "recaptcha required",
    "Reference #",
)

ROLE_SYNONYMS: dict[str, set[str]] = {
    "developer": {"engineer", "dev", "programmer"},
    "engineer": {"developer", "dev", "programmer"},
    "dev": {"developer", "engineer", "programmer"},
    "frontend": {"front-end", "front end"},
    "backend": {"back-end", "back end"},
    "fullstack": {"full stack", "full-stack"},
    "qa": {"quality assurance", "tester", "test"},
}

GENERIC_QUERY_TOKENS = {
    "senior",
    "sr",
    "junior",
    "jr",
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
    "hybrid",
    "onsite",
    "wfh",
    "workfromhome",
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


class NaukriAdapter(SourceAdapter):
    source_name = "naukri"
    implemented = True

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout_seconds: int = NAUKRI_TIMEOUT_SECONDS,
        use_selenium: bool | None = None,
        render_timeout_seconds: int = NAUKRI_RENDER_TIMEOUT_SECONDS,
        headless: bool = False,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.render_timeout_seconds = render_timeout_seconds
        self.headless = headless
        self.use_selenium = session is None if use_selenium is None else use_selenium
        user_agent = clean_text(self.session.headers.get("User-Agent"))
        if not user_agent or user_agent.startswith("python-requests/"):
            self.session.headers["User-Agent"] = NAUKRI_USER_AGENT
        self.session.headers.setdefault(
            "Accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        )
        self.session.headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        self.session.headers.setdefault("Cache-Control", "no-cache")

    def collect(self, title: str, filters: SearchFilters) -> list[Mapping[str, Any]]:
        query = clean_text(title)
        if not query:
            return []

        html = self._fetch_html(query)
        jobs = self._parse_jobs(html, query)
        matched_jobs = [job for job in jobs if self._matches_query(job, query, filters)]

        LOGGER.info(
            "Naukri matched %s of %s jobs for title=%s",
            len(matched_jobs),
            len(jobs),
            query,
        )
        return matched_jobs

    def _fetch_html(self, title: str) -> str:
        search_url = self._build_search_url(title)
        if self.use_selenium:
            try:
                html = self._fetch_html_with_selenium(search_url)
                if not self._looks_blocked(html):
                    return html
                LOGGER.info(
                    "Naukri Selenium render returned a block page for %s; falling back to requests.",
                    search_url,
                )
            except SourceAdapterError as exc:
                LOGGER.warning(
                    "Naukri Selenium render failed for %s; falling back to requests: %s",
                    search_url,
                    exc,
                )
        return self._fetch_html_with_requests(search_url)

    def _fetch_html_with_requests(self, search_url: str) -> str:
        try:
            response = self.session.get(search_url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise SourceAdapterError("Failed to fetch the Naukri search page.") from exc
        return response.text

    def _fetch_html_with_selenium(self, search_url: str) -> str:
        options = self._build_chrome_options()
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
        except WebDriverException as exc:
            raise SourceAdapterError("Failed to launch Selenium for Naukri.") from exc

        try:
            try:
                driver.set_page_load_timeout(self.timeout_seconds)
            except WebDriverException:
                LOGGER.debug("Unable to set Naukri page load timeout in Selenium.", exc_info=True)
            try:
                driver.execute_cdp_cmd(
                    "Network.setUserAgentOverride",
                    {"userAgent": NAUKRI_USER_AGENT, "platform": "Windows"},
                )
            except Exception:
                LOGGER.debug("Unable to override the Chrome user agent for Naukri.", exc_info=True)

            driver.get(search_url)
            try:
                WebDriverWait(driver, self.render_timeout_seconds).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.srp-jobtuple-wrapper"))
                )
            except TimeoutException:
                LOGGER.debug(
                    "Timed out waiting for Naukri job tuples for %s; using current page source.",
                    search_url,
                )
            return driver.page_source
        except WebDriverException as exc:
            raise SourceAdapterError("Failed to render the Naukri search page with Selenium.") from exc
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    LOGGER.debug("Failed to close the Selenium browser cleanly.", exc_info=True)

    def _build_chrome_options(self) -> ChromeOptions:
        options = ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1400,2200")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--lang=en-US")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument(f"--user-agent={NAUKRI_USER_AGENT}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        chrome_binary = self._find_chrome_binary()
        if chrome_binary:
            options.binary_location = chrome_binary
        return options

    def _find_chrome_binary(self) -> str:
        candidates = (
            shutil.which("chrome"),
            shutil.which("chrome.exe"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        )
        for candidate in candidates:
            if candidate and candidate.strip():
                return candidate
        return ""

    def _looks_blocked(self, html: str) -> bool:
        normalized = clean_text(html)
        return any(marker.casefold() in normalized.casefold() for marker in NAUKRI_BLOCKED_MARKERS)

    def _build_search_url(self, title: str) -> str:
        slug = self._slugify(title)
        return NAUKRI_SEARCH_URL_TEMPLATE.format(slug=slug or "jobs")

    def _slugify(self, title: str) -> str:
        tokens = re.findall(r"[a-z0-9]+", repair_mojibake(title).casefold())
        return "-".join(tokens)

    def _parse_jobs(self, html: str, query: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        wrappers = soup.select("div.srp-jobtuple-wrapper")
        if not wrappers:
            wrappers = soup.select("div.cust-job-tuple")

        jobs: list[dict[str, str]] = []
        for wrapper in wrappers:
            record = self._extract_job_record(wrapper, query)
            if record is not None:
                jobs.append(record)

        LOGGER.debug("Naukri parser found %s job tuples", len(jobs))
        return jobs

    def _extract_job_record(
        self,
        wrapper: Tag,
        query: str,
    ) -> dict[str, Any] | None:
        title_node = wrapper.select_one("h2 a.title, a.title")
        if title_node is None:
            return None

        title = self._node_text(title_node, attr="title")
        if not title:
            return None

        company_node = wrapper.select_one(".comp-name")
        location_node = wrapper.select_one(".locWdth, .loc-wrap [title], .loc-wrap")
        description_node = wrapper.select_one(".job-desc")
        posted_node = wrapper.select_one(".job-post-day")
        salary_node = wrapper.select_one(
            ".sal-wrap, .salary, .sal-estimate, .job-salary, .compensation"
        )

        tags = [clean_text(tag.get_text(" ", strip=True)) for tag in wrapper.select(".tags-gt li")]
        description = self._node_text(description_node)

        job_url = ""
        href = clean_text(title_node.get("href"))
        if href:
            job_url = urljoin(NAUKRI_HOME_URL, href)

        return {
            "source": self.source_name,
            "title": title,
            "company": self._node_text(company_node, attr="title"),
            "location": self._node_text(location_node, attr="title"),
            "job_type": self._extract_job_type(tags),
            "salary": self._node_text(salary_node),
            "job_url": job_url,
            "posted_date": self._node_text(posted_node),
            "scraped_at": "",
            "description_snippet": self._build_description_snippet(description),
            "search_keyword": query,
            "_tags": tags,
        }

    def _matches_query(
        self,
        record: Mapping[str, Any],
        query: str,
        filters: SearchFilters,
    ) -> bool:
        title = clean_text(record.get("title"))
        company = clean_text(record.get("company"))
        location = clean_text(record.get("location"))
        description = clean_text(record.get("description_snippet"))
        raw_tags = record.get("_tags", [])
        tags = [clean_text(tag) for tag in raw_tags if clean_text(tag)]

        candidate_blob = self._normalize_text(
            " ".join(
                value
                for value in [title, company, location, description, " ".join(tags)]
                if value
            )
        )
        candidate_tokens = set(self._tokenize(candidate_blob))
        query_tokens = self._query_tokens(query)
        if not query_tokens:
            return True

        # More flexible matching: require at least 50% of query tokens to match
        matched_tokens = sum(1 for token in query_tokens if self._token_matches(token, candidate_tokens))
        if matched_tokens == 0:
            return False
        # If we have multiple tokens, require at least 50% to match
        if len(query_tokens) > 1 and matched_tokens < len(query_tokens) * 0.5:
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

        if filters.remote_only:
            if "remote" not in candidate_blob and "work from home" not in candidate_blob:
                return False

        if filters.experience_level:
            normalized_experience = self._normalize_text(filters.experience_level)
            if normalized_experience not in candidate_blob:
                return False

        if filters.date_posted:
            normalized_filter = clean_text(filters.date_posted).casefold()
            posted_date = clean_text(record.get("posted_date")).casefold()
            if normalized_filter not in posted_date:
                return False

        return True

    def _extract_job_type(self, tags: list[str]) -> str:
        for tag in tags:
            if clean_text(tag).casefold() in JOB_TYPE_TAGS:
                return clean_text(tag)
        return ""

    def _build_description_snippet(self, description: str) -> str:
        text = self._strip_html(description)
        if len(text) <= 240:
            return text
        return text[:240].rstrip() + "..."

    def _strip_html(self, value: object) -> str:
        text = repair_mojibake(value)
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", text)
        return clean_text(text)

    def _node_text(self, node: Tag | None, *, attr: str | None = None) -> str:
        if node is None:
            return ""
        if attr:
            value = clean_text(node.get(attr))
            if value:
                return repair_mojibake(value)
        return repair_mojibake(node.get_text(" ", strip=True))

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
