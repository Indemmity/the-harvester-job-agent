from __future__ import annotations

import csv
import logging
from collections.abc import Sequence
from pathlib import Path

from ..exceptions import PipelineError
from ..models import JOB_CSV_COLUMNS, JobListing
from ..utils import ensure_parent_directory

LOGGER = logging.getLogger(__name__)


class CSVExporter:
    def __init__(self, output_path: Path, append: bool = False) -> None:
        self.output_path = Path(output_path)
        self.append = append

    def export(self, jobs: Sequence[JobListing]) -> Path:
        try:
            ensure_parent_directory(self.output_path)
            mode = "a" if self.append else "w"
            
            # Sort jobs deterministically: by source, then company, then title
            sorted_jobs = sorted(jobs, key=lambda j: (j.source, j.company or "", j.title or ""))
            
            with self.output_path.open(mode, newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=JOB_CSV_COLUMNS)
                # Only write header if not appending or file is empty
                if not self.append or self.output_path.stat().st_size == 0:
                    writer.writeheader()
                for job in sorted_jobs:
                    writer.writerow(job.to_row())
        except OSError as exc:
            raise PipelineError(f"Failed to write CSV output: {self.output_path}") from exc

        LOGGER.info("Wrote %s job rows to %s (mode: %s)", len(sorted_jobs), self.output_path, mode)
        return self.output_path

