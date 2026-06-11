from __future__ import annotations

from collections.abc import Sequence

from ..config import JobAgentConfig
from ..models import JobListing
from .base import BaseJobFilter


class RelevanceFilter(BaseJobFilter):
    """Phase 1 placeholder.

    This keeps the pipeline shape in place while later phases add title and
    description matching rules.
    """

    def apply(self, jobs: Sequence[JobListing], config: JobAgentConfig) -> list[JobListing]:
        return list(jobs)

