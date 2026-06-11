from __future__ import annotations

from collections.abc import Sequence

from ..config import JobAgentConfig
from ..models import JobListing


class BaseJobFilter:
    def apply(self, jobs: Sequence[JobListing], config: JobAgentConfig) -> list[JobListing]:
        raise NotImplementedError

