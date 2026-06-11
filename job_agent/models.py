from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .utils import clean_text

JOB_CSV_COLUMNS: tuple[str, ...] = (
    "source",
    "title",
    "company",
    "location",
    "job_type",
    "salary",
    "job_url",
    "posted_date",
    "scraped_at",
    "description_snippet",
    "search_keyword",
)


@dataclass(slots=True)
class SearchFilters:
    location: str = ""
    remote_only: bool = False
    experience_level: str = ""
    date_posted: str = ""

    def __post_init__(self) -> None:
        self.location = clean_text(self.location)
        self.experience_level = clean_text(self.experience_level)
        self.date_posted = clean_text(self.date_posted)
        self.remote_only = bool(self.remote_only)


@dataclass(slots=True)
class JobListing:
    source: str
    title: str
    company: str = ""
    location: str = ""
    job_type: str = ""
    salary: str = ""
    job_url: str = ""
    posted_date: str = ""
    scraped_at: str = ""
    description_snippet: str = ""
    search_keyword: str = ""

    def __post_init__(self) -> None:
        self.source = clean_text(self.source)
        self.title = clean_text(self.title)
        self.company = clean_text(self.company)
        self.location = clean_text(self.location)
        self.job_type = clean_text(self.job_type)
        self.salary = clean_text(self.salary)
        self.job_url = clean_text(self.job_url)
        self.posted_date = clean_text(self.posted_date)
        self.scraped_at = clean_text(self.scraped_at)
        self.description_snippet = clean_text(self.description_snippet)
        self.search_keyword = clean_text(self.search_keyword)

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[str, Any],
        *,
        fallback_source: str = "",
        fallback_search_keyword: str = "",
        fallback_scraped_at: str = "",
    ) -> "JobListing":
        payload = {
            field_name: clean_text(mapping.get(field_name, ""))
            for field_name in JOB_CSV_COLUMNS
        }
        if not payload["source"]:
            payload["source"] = clean_text(fallback_source)
        if not payload["search_keyword"]:
            payload["search_keyword"] = clean_text(fallback_search_keyword)
        if not payload["scraped_at"]:
            payload["scraped_at"] = clean_text(fallback_scraped_at)
        return cls(**payload)

    def to_row(self) -> dict[str, str]:
        return {column: getattr(self, column) for column in JOB_CSV_COLUMNS}

    def dedupe_key(self) -> str:
        job_url = self.job_url.casefold().strip()
        if job_url:
            return f"url:{job_url}"
        return "composite:" + "|".join(
            (
                self.title.casefold().strip(),
                self.company.casefold().strip(),
                self.location.casefold().strip(),
            )
        )


@dataclass(slots=True)
class JobRunSummary:
    titles: list[str]
    output_path: Path
    total_jobs: int
    source_counts: dict[str, int] = field(default_factory=dict)

