from __future__ import annotations

import logging
from collections.abc import Iterable

from ..exceptions import ConfigurationError
from ..utils import clean_text
from .base import SourceAdapter
from .naukri import NaukriAdapter
from .remoteok import RemoteOKAdapter
from .wellfound import WellfoundAdapter

LOGGER = logging.getLogger(__name__)

SOURCE_ADAPTERS: dict[str, type[SourceAdapter]] = {
    "naukri": NaukriAdapter,
    "remoteok": RemoteOKAdapter,
    "wellfound": WellfoundAdapter,
}


def build_source_adapters(enabled_sources: Iterable[str] | None = None) -> list[SourceAdapter]:
    source_names = SOURCE_ADAPTERS.keys() if enabled_sources is None else enabled_sources
    adapters: list[SourceAdapter] = []

    for source_name in source_names:
        normalized_name = clean_text(source_name).casefold()
        adapter_cls = SOURCE_ADAPTERS.get(normalized_name)
        if adapter_cls is None:
            raise ConfigurationError(f"Unknown source adapter: {source_name!r}")
        adapters.append(adapter_cls())

    LOGGER.debug("Built source adapters: %s", [adapter.source_name for adapter in adapters])
    return adapters
