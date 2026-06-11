#!/usr/bin/env python3
"""Process combined jobs CSV to remove duplicates and generate summary."""

import csv
from collections import Counter
from pathlib import Path

def process_combined_jobs(input_file: Path, output_file: Path) -> dict:
    """Remove duplicates using company + title and generate summary."""
    
    # Read all jobs
    jobs = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append(row)
    
    # Count jobs before deduplication
    total_before = len(jobs)
    
    # Count by source before deduplication
    source_counts_before = Counter(job['source'] for job in jobs)
    
    # Count by role before deduplication
    role_counts_before = Counter(job['search_keyword'] for job in jobs)
    
    # Remove duplicates using company + title
    seen = set()
    unique_jobs = []
    duplicates_removed = 0
    
    for job in jobs:
        # Create dedupe key using company + title
        company = job['company'].strip().lower()
        title = job['title'].strip().lower()
        dedupe_key = f"{company}|{title}"
        
        if dedupe_key not in seen:
            seen.add(dedupe_key)
            unique_jobs.append(job)
        else:
            duplicates_removed += 1
    
    # Count by source after deduplication
    source_counts_after = Counter(job['source'] for job in unique_jobs)
    
    # Count by role after deduplication
    role_counts_after = Counter(job['search_keyword'] for job in unique_jobs)
    
    # Write deduplicated jobs
    if unique_jobs:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=unique_jobs[0].keys())
            writer.writeheader()
            writer.writerows(unique_jobs)
    
    # Generate summary
    summary = {
        'total_before': total_before,
        'total_after': len(unique_jobs),
        'duplicates_removed': duplicates_removed,
        'source_counts_before': dict(source_counts_before),
        'source_counts_after': dict(source_counts_after),
        'role_counts_before': dict(role_counts_before),
        'role_counts_after': dict(role_counts_after),
    }
    
    return summary

def print_summary(summary: dict):
    """Print formatted summary."""
    print("=" * 60)
    print("COMBINED JOBS SUMMARY")
    print("=" * 60)
    print(f"\nTotal jobs before deduplication: {summary['total_before']}")
    print(f"Total jobs after deduplication: {summary['total_after']}")
    print(f"Duplicates removed: {summary['duplicates_removed']}")
    
    print("\n" + "-" * 60)
    print("JOBS PER SOURCE (BEFORE DEDUPLICATION)")
    print("-" * 60)
    for source, count in sorted(summary['source_counts_before'].items()):
        print(f"  {source}: {count}")
    
    print("\n" + "-" * 60)
    print("JOBS PER SOURCE (AFTER DEDUPLICATION)")
    print("-" * 60)
    for source, count in sorted(summary['source_counts_after'].items()):
        print(f"  {source}: {count}")
    
    print("\n" + "-" * 60)
    print("JOBS PER ROLE (BEFORE DEDUPLICATION)")
    print("-" * 60)
    for role, count in sorted(summary['role_counts_before'].items()):
        print(f"  {role}: {count}")
    
    print("\n" + "-" * 60)
    print("JOBS PER ROLE (AFTER DEDUPLICATION)")
    print("-" * 60)
    for role, count in sorted(summary['role_counts_after'].items()):
        print(f"  {role}: {count}")
    
    print("\n" + "=" * 60)
    if summary['total_after'] >= 100:
        print("✅ TARGET ACHIEVED: 100+ jobs")
    elif summary['total_after'] >= 75:
        print("✅ TARGET ACHIEVED: 75+ jobs")
    else:
        print(f"❌ TARGET NOT MET: Need {75 - summary['total_after']} more jobs")
    print("=" * 60)

if __name__ == "__main__":
    input_file = Path("combined_jobs.csv")
    output_file = Path("combined_jobs_deduped.csv")
    
    summary = process_combined_jobs(input_file, output_file)
    print_summary(summary)
    
    print(f"\nDeduplicated jobs saved to: {output_file}")
