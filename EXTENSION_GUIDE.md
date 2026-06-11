# Extension Guide

This guide explains how to extend the job agent with new sources, output formats, and custom functionality.

## Adding New Job Sources

To add a new job source (e.g., LinkedIn, Indeed, Glassdoor), follow these steps:

### 1. Create a New Adapter

Create a new file in `job_agent/adapters/` directory:

```python
# job_agent/adapters/newsource.py
from __future__ import annotations

import logging
from typing import Any, Mapping

from ..exceptions import SourceAdapterError
from ..models import SearchFilters
from .base import SourceAdapter

LOGGER = logging.getLogger(__name__)


class NewSourceAdapter(SourceAdapter):
    source_name = "newsource"
    implemented = True

    def collect(self, title: str, filters: SearchFilters) -> list[Mapping[str, Any]]:
        """
        Collect job listings from the new source.
        
        Args:
            title: Job title to search for
            filters: Search filters (location, experience level, etc.)
            
        Returns:
            List of job records as dictionaries
        """
        # Implement your scraping/API logic here
        # Each record should be a dictionary with at least:
        # - title: str
        # - company: str  
        # - location: str
        # - job_url: str
        # - description: str (optional)
        # - salary: str (optional)
        # - job_type: str (optional)
        # - posted_date: str (optional)
        
        jobs = []
        # ... your implementation ...
        
        return jobs
```

### 2. Register the Adapter

Add your new adapter to the factory in `job_agent/adapters/factory.py`:

```python
from .newsource import NewSourceAdapter

SOURCE_ADAPTER_MAP: dict[str, type[SourceAdapter]] = {
    "naukri": NaukriAdapter,
    "remoteok": RemoteOKAdapter,
    "wellfound": WellfoundAdapter,
    "newsource": NewSourceAdapter,  # Add this line
}
```

### 3. Enable by Default (Optional)

Update `DEFAULT_ENABLED_SOURCES` in `job_agent/config.py`:

```python
DEFAULT_ENABLED_SOURCES: tuple[str, ...] = (
    "naukri",
    "remoteok", 
    "wellfound",
    "newsource",  # Add this line
)
```

### 4. Use the New Source

```bash
# Use all sources including new one
python -m job_agent "Software Engineer"

# Use only specific sources
python -m job_agent "Software Engineer" --sources newsource naukri
```

## Adding New Output Formats

To add a new output format (e.g., XML, database, Parquet), follow these steps:

### 1. Create a New Exporter

Create a new file in `job_agent/exporters/` directory:

```python
# job_agent/exporters/newformat_exporter.py
from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from ..exceptions import PipelineError
from ..models import JobListing
from ..utils import ensure_parent_directory

LOGGER = logging.getLogger(__name__)


class NewFormatExporter:
    """Export job listings to new format."""
    
    def __init__(self, output_path: Path, append: bool = False) -> None:
        self.output_path = Path(output_path)
        self.append = append
    
    def export(self, jobs: Sequence[JobListing]) -> Path:
        """Export jobs to new format."""
        try:
            ensure_parent_directory(self.output_path)
            
            # Convert jobs to your desired format
            jobs_data = [job.to_row() for job in jobs]
            
            # Implement your export logic here
            # ... your implementation ...
            
        except OSError as exc:
            raise PipelineError(f"Failed to write output: {self.output_path}") from exc
        
        LOGGER.info("Wrote %s job rows to %s", len(jobs), self.output_path)
        return self.output_path
```

### 2. Register the Exporter

Add your new exporter to `job_agent/exporters/__init__.py`:

```python
from .csv_exporter import CSVExporter
from .json_exporter import JSONExporter
from .newformat_exporter import NewFormatExporter

__all__ = ["CSVExporter", "JSONExporter", "NewFormatExporter"]
```

### 3. Update Pipeline (Optional)

If you want to support format selection via CLI, update the pipeline to accept custom exporters.

## Scheduling the Job Agent

The job agent includes a scheduler for automated recurring runs:

### Command Line Scheduling

```bash
# Run every hour
python scheduler.py --titles "Software Engineer" --interval 3600

# Run every day with location filter
python scheduler.py --titles "Data Scientist" --location "Bangalore" --interval 86400

# Use configuration file
python scheduler.py --config scheduler_config.json
```

### Configuration File

Create a JSON configuration file:

```json
{
  "titles": ["Software Engineer", "Data Scientist"],
  "location": "Bangalore",
  "interval": 3600,
  "output_dir": "outputs/scheduled"
}
```

### Cron Scheduling (Linux/Mac)

Add to crontab:

```bash
# Run every day at 9 AM
0 9 * * * cd /path/to/job-agent && python -m job_agent "Software Engineer" --location "Bangalore" --output outputs/daily/$(date +\%Y\%m\%d).csv

# Run every hour using scheduler
0 * * * * cd /path/to/job-agent && python scheduler.py --config scheduler_config.json
```

### Windows Task Scheduler

Create a scheduled task to run:
```bash
python -m job_agent "Software Engineer" --location "Bangalore"
```

## Best Practices

1. **Error Handling**: Always wrap external API calls in try-catch blocks and log errors
2. **Rate Limiting**: Respect rate limits of external APIs
3. **Timeouts**: Use appropriate timeouts for network requests
4. **Logging**: Use structured logging for debugging
5. **Testing**: Write unit tests for new adapters
6. **Documentation**: Document your adapter's specific requirements (API keys, authentication, etc.)

## Example: Adding a Simple API Source

```python
# job_agent/adapters/simpleapi.py
import requests
from typing import Any, Mapping

class SimpleAPIAdapter(SourceAdapter):
    source_name = "simpleapi"
    implemented = True
    
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"
    
    def collect(self, title: str, filters: SearchFilters) -> list[Mapping[str, Any]]:
        url = "https://api.example.com/jobs"
        params = {"title": title, "location": filters.location}
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        
        jobs = []
        for item in response.json():
            jobs.append({
                "title": item["job_title"],
                "company": item["company_name"],
                "location": item["location"],
                "job_url": item["apply_url"],
                "description": item.get("description", ""),
                "salary": item.get("salary", ""),
            })
        
        return jobs
```

This extension guide ensures that new adapters can be added without reshaping the core flow, meeting the Phase 8 exit criteria.
