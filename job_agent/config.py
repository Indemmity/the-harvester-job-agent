from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .exceptions import ConfigurationError
from .models import SearchFilters
from .utils import clean_text, dedupe_preserve_order

DEFAULT_ENABLED_SOURCES: tuple[str, ...] = ("naukri", "remoteok", "wellfound")
DEFAULT_OUTPUT_PATH = Path("outputs") / "job_listings.csv"


def generate_output_filename(title: str, location: str | None = None) -> Path:
    """Generate a deterministic output filename based on search parameters."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = title.lower().replace(" ", "-").replace("/", "-")
    if location:
        location_slug = location.lower().replace(" ", "-").replace("/", "-")
        filename = f"{slug}_{location_slug}_{timestamp}.csv"
    else:
        filename = f"{slug}_{timestamp}.csv"
    return Path("outputs") / filename


@dataclass(slots=True)
class JobAgentConfig:
    titles: list[str]
    filters: SearchFilters = field(default_factory=SearchFilters)
    output_path: Path = field(default_factory=lambda: DEFAULT_OUTPUT_PATH)
    enabled_sources: tuple[str, ...] = DEFAULT_ENABLED_SOURCES
    log_level: str = "INFO"
    append: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.titles, str):
            self.titles = [self.titles]
        self.titles = dedupe_preserve_order(self.titles)
        self.output_path = Path(self.output_path)
        self.enabled_sources = normalize_enabled_sources(self.enabled_sources)
        self.log_level = clean_text(self.log_level).upper() or "INFO"


def normalize_titles(values: Iterable[str] | str) -> list[str]:
    if isinstance(values, str):
        values = [values]
    return dedupe_preserve_order(values)


def normalize_enabled_sources(values: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(values, str):
        values = [values]
    return tuple(dedupe_preserve_order(values))


def build_job_agent_config(
    titles: Iterable[str] | str,
    *,
    filters: SearchFilters | None = None,
    output_path: Path | str | None = None,
    enabled_sources: Iterable[str] | None = None,
    log_level: str = "INFO",
    append: bool = False,
) -> JobAgentConfig:
    normalized_titles = normalize_titles(titles)
    if not normalized_titles:
        raise ConfigurationError("At least one job title is required.")

    resolved_filters = filters or SearchFilters()
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    resolved_sources = (
        normalize_enabled_sources(enabled_sources)
        if enabled_sources is not None
        else DEFAULT_ENABLED_SOURCES
    )

    return JobAgentConfig(
        titles=normalized_titles,
        filters=resolved_filters,
        output_path=resolved_output_path,
        enabled_sources=resolved_sources,
        log_level=log_level,
        append=append,
    )
