#!/usr/bin/env python3
"""
Scheduler for job agent - enables automated recurring runs.

This module provides scheduling capabilities for the job agent,
allowing it to run on a regular schedule (e.g., daily, hourly).

Usage:
    python scheduler.py --config config.json
    python scheduler.py --titles "Software Engineer" --location "Bangalore" --interval 3600
"""

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from job_agent.config import build_job_agent_config
from job_agent.logging_config import configure_logging
from job_agent.models import SearchFilters
from job_agent.pipeline import run_job_agent

LOGGER = logging.getLogger(__name__)


class JobScheduler:
    """Scheduler for automated job agent runs."""
    
    def __init__(
        self,
        titles: list[str],
        location: str | None = None,
        interval_seconds: int = 3600,
        output_dir: Path = Path("outputs"),
    ):
        self.titles = titles
        self.location = location
        self.interval_seconds = interval_seconds
        self.output_dir = output_dir
        self.running = False
        
    def run_once(self) -> dict[str, Any]:
        """Run the job agent once and return summary."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"scheduled_run_{timestamp}.csv"
        
        filters = SearchFilters(location=self.location or "")
        
        config = build_job_agent_config(
            titles=self.titles,
            filters=filters,
            output_path=output_path,
        )
        
        summary = run_job_agent(config)
        
        return {
            "timestamp": timestamp,
            "output_path": str(summary.output_path),
            "total_jobs": summary.total_jobs,
            "source_counts": summary.source_counts,
            "titles": summary.titles,
        }
    
    def start(self) -> None:
        """Start the scheduler loop."""
        self.running = True
        LOGGER.info(
            "Starting job scheduler - interval: %ds, titles: %s, location: %s",
            self.interval_seconds,
            self.titles,
            self.location,
        )
        
        while self.running:
            try:
                LOGGER.info("Running scheduled job agent execution")
                result = self.run_once()
                LOGGER.info(
                    "Scheduled run completed: %d jobs written to %s",
                    result["total_jobs"],
                    result["output_path"],
                )
            except Exception:
                LOGGER.exception("Scheduled run failed")
            
            # Wait for next interval
            LOGGER.info("Waiting %d seconds until next run", self.interval_seconds)
            for _ in range(self.interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
    
    def stop(self) -> None:
        """Stop the scheduler."""
        LOGGER.info("Stopping job scheduler")
        self.running = False


def load_config(config_path: Path) -> dict[str, Any]:
    """Load scheduler configuration from JSON file."""
    with config_path.open() as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Job Agent Scheduler")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to JSON configuration file",
    )
    parser.add_argument(
        "--titles",
        nargs="+",
        help="Job titles to search for",
    )
    parser.add_argument(
        "--location",
        help="Location filter",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Interval between runs in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Output directory for scheduled runs",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level",
    )
    
    args = parser.parse_args()
    
    configure_logging(args.log_level)
    
    # Load configuration from file or command line
    if args.config:
        config = load_config(args.config)
        titles = config.get("titles", [])
        location = config.get("location")
        interval = config.get("interval", args.interval)
        output_dir = Path(config.get("output_dir", args.output_dir))
    else:
        if not args.titles:
            print("Error: --titles or --config is required")
            return 1
        titles = args.titles
        location = args.location
        interval = args.interval
        output_dir = args.output_dir
    
    scheduler = JobScheduler(
        titles=titles,
        location=location,
        interval_seconds=interval,
        output_dir=output_dir,
    )
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        LOGGER.info("Received signal %s, shutting down", signum)
        scheduler.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        LOGGER.info("Keyboard interrupt, shutting down")
        scheduler.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
