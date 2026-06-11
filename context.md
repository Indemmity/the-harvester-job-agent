# Job Agent Context

## Problem Statement
We need to build a job aggregation agent that searches for jobs matching a relevant title across multiple job boards, then stores the discovered results in a CSV file.

The initial target sources are:
- Naukri
- RemoteOK
- Wellfound

The agent should help collect jobs for a given title or set of titles, normalize the results into a common structure, remove duplicates, and persist the final list to CSV.

## Goal
Create a reliable workflow that:
1. Accepts a job title or keyword.
2. Searches the supported job boards for matching listings.
3. Filters results so only relevant jobs are kept.
4. Normalizes the job data into one consistent schema.
5. Writes the final results to a CSV file for later use.

## Scope
### In Scope
- Querying the supported job sources for a specific title
- Collecting basic job metadata
- Deduplicating repeated jobs across sources
- Exporting results to CSV
- Keeping the output structure stable and easy to extend later

## Source Collection Strategy
Use the most appropriate collection method for each source.

### Naukri
- Use Selenium to render the search page
- Parse the rendered HTML with `BeautifulSoup`
- Be careful with selectors because the page structure can change
- Treat it as selector-driven browser scraping with defensive parsing

### RemoteOK
- Use the public API
- Hit `/api` and consume JSON directly
- This should be the fastest source to integrate
- Always check for an API before considering HTML scraping

### Wellfound
- Use Firecrawl
- Treat it as JavaScript-rendered
- Let Firecrawl handle the rendered page content
- Expect clean, structured output from the extraction flow

### Out of Scope for the first version
- Applying to jobs automatically
- Sending emails or notifications
- Building a full web UI
- Ranking jobs with complex ML logic
- Storing data in a database before CSV export

## Expected Inputs
- Job title or title keywords
- Optional filters such as:
  - location
  - remote only
  - experience level
  - date posted

## Expected Outputs
The agent should generate a CSV file containing one row per unique job.

Recommended columns:
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

## Core Workflow
1. Receive the target title.
2. Search each configured source.
3. Parse the job listings from each source.
4. Normalize fields into a shared schema.
5. Filter out jobs that are not relevant to the title.
6. Deduplicate jobs that appear more than once.
7. Save the final dataset to CSV.

## Relevance Rule
A job should be considered relevant when the title or description is meaningfully aligned with the requested role.

Examples:
- For `Data Analyst`, keep roles such as `Junior Data Analyst`, `Business Analyst` only if the description strongly matches the target intent.
- For `Backend Developer`, keep roles like `Python Backend Engineer`, `API Engineer`, or similar variants.

The exact matching logic should be simple at first and can be improved later.

## Data Handling Notes
- Prefer a stable canonical ID if a source provides one.
- Otherwise deduplicate using a combination of:
  - title
  - company
  - location
  - job URL
- Normalize missing fields to empty strings rather than failing the pipeline.
- Keep timestamps in a consistent format.

## Implementation Considerations
- Respect the source websites' terms, robots rules, and rate limits.
- Keep Naukri scraping isolated so selector changes are easy to fix.
- Prefer RemoteOK's API over any HTML scraping approach.
- Use Firecrawl for Wellfound instead of hand-rolled browser automation.
- Expect that page structures may change, so source-specific parsers should be isolated.
- Build the pipeline so each source can be added, removed, or repaired independently.
- Make the CSV export deterministic so repeated runs are easy to compare.

## Success Criteria
The solution is successful when:
- It can search all three sources for a given title.
- It returns a clean list of relevant jobs.
- It saves the results to CSV without duplicates.
- The structure is clear enough to extend later with new sources or storage options.

## Assumptions
- The agent will run on demand or on a schedule.
- Search results may vary between runs depending on source availability.
- The first version prioritizes correctness and maintainability over advanced ranking.

## Open Questions
- Should the agent support one title at a time or multiple titles in one run?
- Should the CSV be overwritten each run or appended to?
- Do we want a minimum similarity threshold for relevance filtering?
- Should we store raw source payloads for debugging?
