from __future__ import annotations

from typing import Any, Mapping

from ..models import SearchFilters


class SourceAdapter:
    source_name = "unknown"
    implemented = False

    def collect(self, title: str, filters: SearchFilters) -> list[Mapping[str, Any]]:
        raise NotImplementedError(f"{self.source_name} is not implemented yet.")

