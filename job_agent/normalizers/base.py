from __future__ import annotations

from typing import Any, Mapping

from ..models import JobListing


class BaseNormalizer:
    def normalize(
        self,
        record: Mapping[str, Any],
        *,
        source: str,
        search_keyword: str,
        scraped_at: str,
    ) -> JobListing:
        raise NotImplementedError

