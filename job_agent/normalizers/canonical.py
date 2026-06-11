from __future__ import annotations

from typing import Any, Mapping

from ..models import JobListing
from .base import BaseNormalizer


class CanonicalJobNormalizer(BaseNormalizer):
    def normalize(
        self,
        record: Mapping[str, Any],
        *,
        source: str,
        search_keyword: str,
        scraped_at: str,
    ) -> JobListing:
        payload = dict(record)
        payload.setdefault("source", source)
        payload.setdefault("search_keyword", search_keyword)
        payload.setdefault("scraped_at", scraped_at)
        return JobListing.from_mapping(
            payload,
            fallback_source=source,
            fallback_search_keyword=search_keyword,
            fallback_scraped_at=scraped_at,
        )

