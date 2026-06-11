from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from .config import build_job_agent_config
from .exceptions import JobAgentError
from .logging_config import configure_logging
from .models import SearchFilters
from .pipeline import run_job_agent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the job aggregation agent scaffold.")
    parser.add_argument(
        "titles",
        nargs="*",
        help="Job title or keyword to search for. Multiple words are treated as one title.",
    )
    parser.add_argument(
        "--title",
        dest="title_flags",
        action="append",
        default=[],
        help="Add an explicit title or keyword. Can be repeated.",
    )
    parser.add_argument("--location", default="", help="Optional location filter.")
    parser.add_argument(
        "--remote-only",
        action="store_true",
        help="Restrict results to remote opportunities.",
    )
    parser.add_argument(
        "--experience-level",
        default="",
        help="Optional experience level filter.",
    )
    parser.add_argument(
        "--date-posted",
        default="",
        help="Optional recency filter.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output file path.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        help="Job sources to run (e.g., naukri remoteok wellfound). If not specified, runs all enabled sources.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing output file instead of overwriting.",
    )
    return parser


def _parse_titles(args: argparse.Namespace) -> list[str]:
    titles: list[str] = []
    titles.extend(args.title_flags or [])
    if args.titles:
        titles.append(" ".join(args.titles))
    return [title.strip() for title in titles if title and title.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    parser = _build_parser()
    args = parser.parse_args(argv)

    titles = _parse_titles(args)
    if not titles:
        parser.error("at least one job title is required")

    configure_logging(args.log_level)
    logger = logging.getLogger(__name__)

    config = build_job_agent_config(
        titles,
        filters=SearchFilters(
            location=args.location,
            remote_only=args.remote_only,
            experience_level=args.experience_level,
            date_posted=args.date_posted,
        ),
        output_path=args.output,
        enabled_sources=args.sources if args.sources else None,
        log_level=args.log_level,
        append=args.append,
    )

    try:
        summary = run_job_agent(config)
    except JobAgentError as exc:
        logger.error("%s", exc)
        return 2
    except Exception:
        logger.exception("Unexpected failure while running the job agent.")
        return 1

    print(
        f"Job agent completed for {', '.join(summary.titles)}: "
        f"{summary.total_jobs} jobs written to {summary.output_path}"
    )
    return 0

