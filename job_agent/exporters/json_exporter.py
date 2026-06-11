from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

from ..exceptions import PipelineError
from ..models import JobListing
from ..utils import ensure_parent_directory

LOGGER = logging.getLogger(__name__)


class JSONExporter:
    """Export job listings to JSON format."""
    
    def __init__(self, output_path: Path, append: bool = False) -> None:
        self.output_path = Path(output_path)
        self.append = append
    
    def export(self, jobs: Sequence[JobListing]) -> Path:
        """Export jobs to JSON file."""
        try:
            ensure_parent_directory(self.output_path)
            
            # Convert jobs to dictionaries
            jobs_data = [job.to_row() for job in jobs]
            
            if self.append and self.output_path.exists():
                # Read existing data and append
                with self.output_path.open("r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, list):
                    jobs_data = existing_data + jobs_data
                else:
                    jobs_data = [existing_data] + jobs_data
            
            with self.output_path.open("w", encoding="utf-8") as f:
                json.dump(jobs_data, f, indent=2, ensure_ascii=False)
                
        except OSError as exc:
            raise PipelineError(f"Failed to write JSON output: {self.output_path}") from exc
        except json.JSONDecodeError as exc:
            raise PipelineError(f"Failed to parse existing JSON file: {self.output_path}") from exc
        
        LOGGER.info("Wrote %s job rows to %s (mode: %s)", len(jobs_data), self.output_path, "append" if self.append else "write")
        return self.output_path
