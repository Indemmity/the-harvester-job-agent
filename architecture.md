# Job Agent Architecture

This architecture is based on [context.md](context.md) and breaks the project into buildable phases.

## System Overview
The job agent should follow a simple pipeline:

1. Accept a job title or keyword.
2. Fetch jobs from each configured source using the correct integration method.
3. Normalize all results into one shared schema.
4. Filter for relevance.
5. Deduplicate jobs across sources.
6. Export the final dataset to CSV.

## Core Components

### 1. Input Layer
Responsible for accepting:
- job title or keyword
- optional filters such as location, remote-only, experience level, and date posted

This layer should stay thin and only validate basic input shape.

### 2. Source Adapters
Each source gets its own adapter so collection logic stays isolated.

- `NaukriAdapter`
  - Selenium-rendered HTML scraping
  - `BeautifulSoup` selector parsing
  - selector-driven parsing

- `RemoteOKAdapter`
  - public API client
  - `/api` JSON parsing

- `WellfoundAdapter`
  - Firecrawl-based extraction
  - handles JavaScript-rendered content

Each adapter should return raw job records in a source-specific format before normalization.

### 3. Normalization Layer
Transforms raw source payloads into a shared job schema.

Suggested canonical fields:
- source
- title
- company
- location
- job_type
- salary
- job_url
- posted_date
- scraped_at
- description_snippet
- search_keyword

### 4. Relevance Filter
Keeps only listings aligned with the requested role.

Initial approach:
- exact keyword matches on title
- lightweight keyword similarity in description
- conservative false-positive handling

### 5. Deduplication Layer
Removes repeated jobs across sources.

Preferred dedupe order:
1. source canonical ID, if available
2. job URL
3. composite fingerprint from title + company + location

### 6. CSV Exporter
Writes the final normalized job list to CSV.

Responsibilities:
- stable column order
- deterministic output
- safe handling of missing values
- consistent timestamps

### 7. Orchestration Layer
Coordinates the full run:
- accepts input
- triggers each source adapter
- merges results
- filters, dedupes, exports

This can be implemented as a CLI, a script entry point, or a scheduled worker.

## Phase-Wise Architecture

### Phase 1: Project Foundation
Goal: establish the project structure and shared contracts.

Build:
- folder structure for adapters, normalizers, filters, exporters, and orchestration
- shared job schema / data model
- configuration for titles, filters, and output path
- logging and error handling baseline

Deliverables:
- runnable skeleton
- stable data contract
- predictable project layout

Exit Criteria:
- the project can start and accept a job title without failing
- the canonical schema is defined and reused everywhere

### Phase 2: RemoteOK Integration
Goal: integrate the fastest and cleanest source first.

Build:
- `RemoteOKAdapter`
- Hit https://remoteok.com/api with User-Agent header
- Filter returned JSON array by matching job title (case-insensitive)
- Map fields (position, company, location, url, date) to canonical schema
- No pagination needed - API returns all recent listings in one call

Why this phase comes first:
- the API path is simpler than scraping
- it validates the end-to-end pipeline quickly

Deliverables:
- working RemoteOK data fetch
- normalized job records
- sample CSV output for one source

Exit Criteria:
- RemoteOK results are fetched and exported successfully
- the pipeline handles empty and missing fields cleanly

### Phase 3: Naukri HTML Scraping
Goal: add the server-rendered HTML source.

Build:
- `NaukriAdapter`
- Selenium page rendering
- `BeautifulSoup` + selector extraction
- selector-based extraction
- defensive parsing for HTML changes

Important design note:
- isolate selector logic so page changes are easy to patch
- keep parsing small and testable

Deliverables:
- Naukri scraper module
- normalized Naukri records
- shared error handling for selector failures

Exit Criteria:
- Naukri jobs can be scraped and normalized for a target title
- selector failures do not break the full run

### Phase 4: Wellfound via Firecrawl
Goal: integrate the JavaScript-rendered source through Firecrawl.

Build:
- `WellfoundAdapter`
- Firecrawl extraction flow
- response mapping into the canonical schema

Why this phase matters:
- it avoids brittle browser automation
- it keeps JS-rendered handling outside the core pipeline

Deliverables:
- Firecrawl-backed Wellfound integration
- normalized Wellfound job records

Exit Criteria:
- Wellfound results are collected in structured form
- output fields align with the shared schema

### Phase 5: Multi-Source Orchestration with Location Filtering
Goal: accept job role and location from user, then trigger all three job boards (Naukri, RemoteOK, Wellfound) with proper filtering.

Build:
- CLI input for job title/role and optional location
- Source selection mechanism (--sources flag to run specific boards or all)
- Location filtering applied to each source adapter
- Unified output from all sources

Suggested behavior:
- User provides job title/role (e.g., "Software Engineer")
- User optionally provides location (e.g., "Bangalore")
- System triggers all three sources (Naukri, RemoteOK, Wellfound) by default
- Each source applies location filtering if provided
- Results are aggregated and exported to single CSV

Deliverables:
- CLI that accepts job role and location
- Multi-source execution (Naukri, RemoteOK, Wellfound)
- Location-filtered results from each source
- Unified CSV output with all sources

Exit Criteria:
- All three sources can be triggered simultaneously
- Location filtering works across all sources
- Results are properly aggregated in output CSV

### Phase 6: CSV Export and Run Packaging
Goal: turn the pipeline into a repeatable output generator.

Build:
- CSV writer
- deterministic row ordering
- output file naming strategy
- overwrite vs append policy

Recommended default:
- overwrite per run unless you explicitly need history tracking

Deliverables:
- one clean CSV file per run
- stable column ordering

Exit Criteria:
- the same input produces comparable output structure
- the CSV opens cleanly in spreadsheet tools

### Phase 7: Hardening and Operational Quality
Goal: make the agent resilient enough for regular use.

Build:
- retries and backoff where appropriate
- timeouts per source
- structured logging
- source-level failure isolation
- validation for malformed records

Deliverables:
- more reliable runs
- easier debugging when a source changes

Exit Criteria:
- one failing source does not collapse the entire job run
- logs are useful enough to diagnose parsing and API issues

### Phase 8: Scheduling and Future Extensions
Goal: prepare the agent for recurring runs and future growth.

Build:
- scheduled execution
- optional persistence beyond CSV
- support for multiple titles in one run
- additional job sources later

Deliverables:
- automation-ready job agent
- extension points for new sources and output formats

Exit Criteria:
- the pipeline can run on a schedule or trigger
- new adapters can be added without reshaping the core flow

## Recommended Execution Order
1. Define the shared schema and folder structure.
2. Integrate RemoteOK first.
3. Add Naukri scraping.
4. Add Wellfound through Firecrawl.
5. Add relevance filtering and deduplication.
6. Finalize CSV export.
7. Harden logging, retries, and validation.
8. Add scheduling and optional extensions.

## Notes on Design Choices
- Keep source-specific parsing isolated.
- Prefer API and structured extraction over brittle scraping where possible.
- Make normalization the single shared contract between sources and export.
- Keep the first version focused on correctness and maintainability.
- Treat CSV as the first durable output, not the final storage layer.
