# Job Agent

A Python-based job aggregation agent that searches for jobs across multiple job boards, normalizes the results, filters for relevance, and exports them to CSV.

## Features

- **Multi-source job aggregation**: Fetches jobs from Naukri, RemoteOK, and Wellfound
- **Intelligent filtering**: Filters jobs by location, remote status, experience level, and posting date
- **Relevance matching**: Keeps only jobs relevant to your search keywords
- **Deduplication**: Removes duplicate job listings across sources
- **CSV export**: Exports clean, normalized job data to CSV files
- **CLI interface**: Easy-to-use command-line interface

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/job-agent.git
cd job-agent
```

2. Install dependencies:
```bash
pip install -e .
```

3. Install additional dependencies:
```bash
pip install python-dotenv
```

4. Create a `.env` file in the project root (optional, for environment-specific configuration)

## Usage

### Basic Usage

Search for jobs with a specific title:
```bash
job-agent "Software Engineer"
```

### Advanced Usage

Search with location filter:
```bash
job-agent "Data Scientist" --location "Bangalore"
```

Search for remote-only jobs:
```bash
job-agent "Backend Developer" --remote-only
```

Search with multiple filters:
```bash
job-agent "Product Manager" --location "Remote" --experience-level "Senior" --date-posted "7"
```

Specify output file:
```bash
job-agent "DevOps Engineer" --output jobs.csv
```

Run specific sources only:
```bash
job-agent "Full Stack Developer" --sources naukri remoteok
```

Append to existing output file:
```bash
job-agent "ML Engineer" --append
```

### CLI Options

- `titles` (positional): Job title or keyword to search for
- `--title`: Add an explicit title (can be repeated)
- `--location`: Optional location filter
- `--remote-only`: Restrict to remote opportunities
- `--experience-level`: Optional experience level filter
- `--date-posted`: Optional recency filter (days)
- `--output`: CSV output file path
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `--sources`: Specific job sources to run (naukri, remoteok, wellfound)
- `--append`: Append to existing output file instead of overwriting

## Architecture

The job agent follows a modular pipeline architecture:

1. **Input Layer**: Accepts job titles and optional filters
2. **Source Adapters**: Each job board has its own adapter for data collection
   - Naukri: Selenium-rendered HTML scraping
   - RemoteOK: Public API client
   - Wellfound: Firecrawl-based extraction
3. **Normalization Layer**: Transforms raw data into a shared schema
4. **Relevance Filter**: Keeps only listings aligned with the requested role
5. **Deduplication Layer**: Removes repeated jobs across sources
6. **CSV Exporter**: Writes final dataset to CSV
7. **Orchestration Layer**: Coordinates the full pipeline

### Data Schema

Normalized job records include:
- `source`: Job board name
- `title`: Job title
- `company`: Company name
- `location`: Job location
- `job_type`: Full-time, part-time, contract, etc.
- `salary`: Salary information
- `job_url`: Link to job posting
- `posted_date`: When the job was posted
- `scraped_at`: Timestamp when data was collected
- `description_snippet`: Brief job description
- `search_keyword`: The search term used

## Project Structure

```
job-agent/
├── job_agent/
│   ├── adapters/          # Source-specific adapters
│   ├── exporters/         # Data export modules
│   ├── filters/           # Relevance and other filters
│   ├── models.py          # Data models
│   ├── pipeline.py        # Main orchestration logic
│   ├── cli.py             # Command-line interface
│   └── config.py          # Configuration management
├── tests/                 # Test files
├── docs/                  # Documentation
├── outputs/               # Generated CSV files
├── architecture.md        # Detailed architecture documentation
├── context.md            # Project context and scope
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Adding New Sources

To add a new job source:

1. Create a new adapter in `job_agent/adapters/`
2. Inherit from the base adapter class
3. Implement the required methods for data collection
4. Add normalization logic for the source-specific format
5. Register the adapter in the factory

See `EXTENSION_GUIDE.md` for detailed instructions.

## Dependencies

- beautifulsoup4>=4.12
- requests>=2.31
- selenium>=4.44
- python-dotenv

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with reference to modern Python packaging best practices
- Uses established libraries for web scraping and data processing


## Results

- Total jobs collected: 332
- After deduplication: 286 unique jobs

### Sources
- Naukri
- RemoteOK
- Wellfound

### Roles Collected
- Software Engineer
- Data Scientist
- Product Manager

### Output Files
- combined_jobs.csv
- combined_jobs_deduped.csv
