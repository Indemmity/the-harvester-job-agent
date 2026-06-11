from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping, Sequence

from .adapters import SourceAdapter, build_source_adapters
from .config import JobAgentConfig
from .exceptions import ConfigurationError
from .exporters import CSVExporter
from .filters import RelevanceFilter
from .models import JobListing, JobRunSummary
from .normalizers import CanonicalJobNormalizer
from .utils import utc_now_iso

LOGGER = logging.getLogger(__name__)


def _dedupe_jobs(jobs: Sequence[JobListing]) -> list[JobListing]:
    seen: set[str] = set()
    result: list[JobListing] = []
    for job in jobs:
        key = job.dedupe_key()
        if key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result


class JobAgentPipeline:
    def __init__(
        self,
        config: JobAgentConfig,
        *,
        source_adapters: Sequence[SourceAdapter] | None = None,
        normalizer: CanonicalJobNormalizer | None = None,
        job_filter: RelevanceFilter | None = None,
        exporter: CSVExporter | None = None,
    ) -> None:
        self.config = config
        self.source_adapters = (
            list(source_adapters)
            if source_adapters is not None
            else build_source_adapters(config.enabled_sources)
        )
        self.normalizer = normalizer or CanonicalJobNormalizer()
        self.job_filter = job_filter or RelevanceFilter()
        self.exporter = exporter or CSVExporter(config.output_path, append=config.append)

    def run(self) -> JobRunSummary:
        if not self.config.titles:
            raise ConfigurationError("At least one job title is required.")

        scraped_at = utc_now_iso()
        jobs: list[JobListing] = []
        source_counts: Counter[str] = Counter()

        active_adapters = [adapter for adapter in self.source_adapters if adapter.implemented]
        if not active_adapters:
            LOGGER.info("No source adapters are implemented yet; exporting an empty CSV scaffold.")

        for title in self.config.titles:
            for adapter in active_adapters:
                try:
                    raw_records = adapter.collect(title, self.config.filters)
                except NotImplementedError:
                    LOGGER.info("Skipping unimplemented source adapter: %s", adapter.source_name)
                    continue
                except Exception:
                    LOGGER.exception(
                        "Source adapter failed for source=%s title=%s",
                        adapter.source_name,
                        title,
                    )
                    continue

                for raw_record in raw_records:
                    # Validate malformed records
                    if not isinstance(raw_record, Mapping):
                        LOGGER.warning(
                            "Skipping malformed record (not a mapping) for source=%s title=%s",
                            adapter.source_name,
                            title,
                        )
                        continue
                    
                    # Ensure required fields exist
                    if not raw_record.get("title") and not raw_record.get("company"):
                        LOGGER.warning(
                            "Skipping malformed record (missing title and company) for source=%s title=%s",
                            adapter.source_name,
                            title,
                        )
                        continue
                    
                    try:
                        job = self.normalizer.normalize(
                            raw_record,
                            source=adapter.source_name,
                            search_keyword=title,
                            scraped_at=scraped_at,
                        )
                    except Exception:
                        LOGGER.exception(
                            "Failed to normalize a record for source=%s title=%s",
                            adapter.source_name,
                            title,
                        )
                        continue

                    jobs.append(job)
                    source_counts[job.source or adapter.source_name] += 1

        filtered_jobs = self.job_filter.apply(jobs, self.config)
        deduped_jobs = _dedupe_jobs(filtered_jobs)
        output_path = self.exporter.export(deduped_jobs)

        return JobRunSummary(
            titles=list(self.config.titles),
            output_path=output_path,
            total_jobs=len(deduped_jobs),
            source_counts=dict(source_counts),
        )


def run_job_agent(config: JobAgentConfig) -> JobRunSummary:
    return JobAgentPipeline(config).run()

